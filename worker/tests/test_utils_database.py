from datetime import datetime
from unittest.mock import MagicMock, patch, call, ANY
from uuid import uuid4

import pytest

from utils.database import (
    Db,
    read_database_credentials_from_ssm,
    connection_string,
    fetch_email_by_id,
    fetch_scheduled_emails_to_run,
    update_email_state,
    lock_email,
    fail_email,
    succeed_email,
)
from utils.types import (
    DatabaseCredentials,
    NotFoundError,
    ScheduledEmail,
    ScheduledEmailStatus,
)


@patch("utils.database.read_ssm_parameter")
def test_read_database_credentials_from_ssm(mock_read_ssm_parameter: MagicMock) -> None:
    # Arrange
    mock_read_ssm_parameter.side_effect = [
        {"Value": "localhost"},
        {"Value": "5432"},
        {"Value": "amy"},
        {"Value": "fakeUser"},
        {"Value": "fakePassword"},
    ]
    expected_credentials = DatabaseCredentials(
        HOST="localhost",
        PORT="5432",
        USER="fakeUser",
        PASSWORD="fakePassword",
        NAME="amy",
    )

    # Act
    credentials = read_database_credentials_from_ssm("staging")

    # Assert
    assert credentials == expected_credentials
    mock_read_ssm_parameter.assert_has_calls(
        [
            call("/staging/amy/database_host"),
            call("/staging/amy/database_port"),
            call("/staging/amy/database_name"),
            call("/staging/amy/database_user"),
            call("/staging/amy/database_password"),
        ]
    )


def test_connection_string() -> None:
    # Arrange
    credentials = DatabaseCredentials(
        HOST="localhost",
        PORT="5432",
        USER="fakeUser",
        PASSWORD="fakePassword",
        NAME="amy",
    )
    expected_connection_string = "postgresql://fakeUser:fakePassword@localhost:5432/amy"

    # Act
    connection_str = connection_string(credentials)

    # Assert
    assert connection_str == expected_connection_string


@patch.object(Db, "select_scheduled_email")
def test_fetch_email_by_id(mock_select_scheduled_email: MagicMock) -> None:
    # Arrange
    id_ = uuid4()
    template_id = uuid4()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {
        "id": id_,
        "created_at": "2021-06-01T00:00:00+00:00",
        "last_updated_at": "2021-06-01T00:00:00+00:00",
        "state": "scheduled",
        "scheduled_at": "2021-06-01T00:00:00+00:00",
        "to_header": [""],
        "from_header": "",
        "reply_to_header": "",
        "cc_header": [""],
        "bcc_header": [""],
        "subject": "",
        "body": "",
        "template_id": template_id,
    }

    # Act
    result = fetch_email_by_id(id_, mock_cursor)

    # Assert
    mock_select_scheduled_email.assert_called_once_with(mock_cursor, id_)
    assert result == ScheduledEmail(
        id=id_,
        created_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        last_updated_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        state=ScheduledEmailStatus("scheduled"),
        scheduled_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        to_header=[""],
        from_header="",
        reply_to_header="",
        cc_header=[""],
        bcc_header=[""],
        subject="",
        body="",
        template_id=template_id,
    )


def test_fetch_email_by_id__failed() -> None:
    # Arrange
    id_ = uuid4()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    # Act & Assert
    with pytest.raises(NotFoundError):
        fetch_email_by_id(id_, mock_cursor)


@patch.object(Db, "select_scheduled_emails")
def test_fetch_scheduled_emails(mock_select_scheduled_emails: MagicMock) -> None:
    # Arrange
    id1 = uuid4()
    id2 = uuid4()
    template_id1 = uuid4()
    template_id2 = uuid4()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {
            "id": id1,
            "created_at": "2021-06-01T00:00:00+00:00",
            "last_updated_at": "2021-06-01T00:00:00+00:00",
            "state": "scheduled",
            "scheduled_at": "2021-06-01T00:00:00+00:00",
            "to_header": [""],
            "from_header": "",
            "reply_to_header": "",
            "cc_header": [""],
            "bcc_header": [""],
            "subject": "",
            "body": "",
            "template_id": template_id1,
        },
        {
            "id": id2,
            "created_at": "2022-06-01T00:00:00+00:00",
            "last_updated_at": "2022-06-01T00:00:00+00:00",
            "state": "failed",
            "scheduled_at": "2022-06-01T00:00:00+00:00",
            "to_header": [""],
            "from_header": "",
            "reply_to_header": "",
            "cc_header": [""],
            "bcc_header": [""],
            "subject": "",
            "body": "",
            "template_id": template_id2,
        },
    ]

    # Act
    result = fetch_scheduled_emails_to_run(mock_cursor)

    # Assert
    mock_select_scheduled_emails.assert_called_once_with(mock_cursor, timestamp=ANY)
    assert result == [
        ScheduledEmail(
            id=id1,
            created_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
            last_updated_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
            state=ScheduledEmailStatus("scheduled"),
            scheduled_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
            to_header=[""],
            from_header="",
            reply_to_header="",
            cc_header=[""],
            bcc_header=[""],
            subject="",
            body="",
            template_id=template_id1,
        ),
        ScheduledEmail(
            id=id2,
            created_at=datetime.fromisoformat("2022-06-01T00:00:00+00:00"),
            last_updated_at=datetime.fromisoformat("2022-06-01T00:00:00+00:00"),
            state=ScheduledEmailStatus("failed"),
            scheduled_at=datetime.fromisoformat("2022-06-01T00:00:00+00:00"),
            to_header=[""],
            from_header="",
            reply_to_header="",
            cc_header=[""],
            bcc_header=[""],
            subject="",
            body="",
            template_id=template_id2,
        ),
    ]


@patch("utils.database.fetch_email_by_id")
@patch.object(Db, "update_scheduled_email_status")
@patch.object(Db, "insert_scheduled_email_log")
def test_update_email_state(
    mock_insert_scheduled_email_log: MagicMock,
    mock_update_scheduled_email_status: MagicMock,
    mock_fetch_email: MagicMock,
) -> None:
    # Arrange
    id_ = uuid4()
    template_id = uuid4()
    email = ScheduledEmail(
        id=id_,
        created_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        last_updated_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        state=ScheduledEmailStatus("scheduled"),
        scheduled_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        to_header=[""],
        from_header="",
        reply_to_header="",
        cc_header=[""],
        bcc_header=[""],
        subject="",
        body="",
        template_id=template_id,
    )
    new_state = ScheduledEmailStatus("failed")
    mock_cursor = MagicMock()

    fetched = email.model_copy()
    fetched.state = ScheduledEmailStatus("failed")
    mock_fetch_email.return_value = fetched

    # Act
    result = update_email_state(
        email,
        new_state,
        mock_cursor,
        details="Test state change",
    )

    # Assert
    assert result == ScheduledEmail(
        id=id_,
        created_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        last_updated_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        state=ScheduledEmailStatus("failed"),
        scheduled_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        to_header=[""],
        from_header="",
        reply_to_header="",
        cc_header=[""],
        bcc_header=[""],
        subject="",
        body="",
        template_id=template_id,
    )
    mock_update_scheduled_email_status.assert_called_once_with(
        mock_cursor, id_, new_state
    )
    mock_insert_scheduled_email_log.assert_called_once_with(
        mock_cursor,
        ANY,
        ANY,
        "Test state change",
        ScheduledEmailStatus("scheduled"),
        new_state,
        id_,
    )


@patch("utils.database.update_email_state")
def test_lock_email(mock_update_email_state: MagicMock) -> None:
    # Arrange
    id_ = uuid4()
    template_id = uuid4()
    email = ScheduledEmail(
        id=id_,
        created_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        last_updated_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        state=ScheduledEmailStatus("scheduled"),
        scheduled_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        to_header=[""],
        from_header="",
        reply_to_header="",
        cc_header=[""],
        bcc_header=[""],
        subject="",
        body="",
        template_id=template_id,
    )
    mock_cursor = MagicMock()

    # Act
    lock_email(email, mock_cursor)

    # Assert
    assert mock_update_email_state.called_once_with(
        email, ScheduledEmailStatus.LOCKED, mock_cursor
    )


@patch("utils.database.update_email_state")
def test_fail_email(mock_update_email_state: MagicMock) -> None:
    # Arrange
    id_ = uuid4()
    template_id = uuid4()
    email = ScheduledEmail(
        id=id_,
        created_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        last_updated_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        state=ScheduledEmailStatus("scheduled"),
        scheduled_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        to_header=[""],
        from_header="",
        reply_to_header="",
        cc_header=[""],
        bcc_header=[""],
        subject="",
        body="",
        template_id=template_id,
    )
    mock_cursor = MagicMock()

    # Act
    fail_email(email, "failure details", mock_cursor)

    # Assert
    assert mock_update_email_state.called_once_with(
        email, ScheduledEmailStatus.FAILED, mock_cursor, details="failure details"
    )


@patch("utils.database.update_email_state")
def test_succeed_email(mock_update_email_state: MagicMock) -> None:
    # Arrange
    id_ = uuid4()
    template_id = uuid4()
    email = ScheduledEmail(
        id=id_,
        created_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        last_updated_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        state=ScheduledEmailStatus("scheduled"),
        scheduled_at=datetime.fromisoformat("2021-06-01T00:00:00+00:00"),
        to_header=[""],
        from_header="",
        reply_to_header="",
        cc_header=[""],
        bcc_header=[""],
        subject="",
        body="",
        template_id=template_id,
    )
    mock_cursor = MagicMock()

    # Act
    succeed_email(email, "success details", mock_cursor)

    # Assert
    assert mock_update_email_state.called_once_with(
        email, ScheduledEmailStatus.LOCKED, mock_cursor, details="success details"
    )
