from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from psycopg.cursor_async import AsyncCursor

from src.ssm import get_parameter_value, read_ssm_parameter
from src.types import (
    DatabaseCredentials,
    NotFoundError,
    ScheduledEmail,
    ScheduledEmailStatus,
)


class Db:
    """Thin wrapper for DB queries. All methods are static and take a cursor
    as a first argument, and every method executes a query and returns the cursor."""

    @staticmethod
    async def select_scheduled_email(
        cursor: AsyncCursor[Any], id: UUID
    ) -> AsyncCursor[Any]:
        return await cursor.execute(
            """
            SELECT
                id, created_at, last_updated_at, state, scheduled_at,
                to_header, from_header, reply_to_header, cc_header, bcc_header,
                subject, body, template_id
            FROM emails_scheduledemail
            WHERE id = %s
            """,
            (id,),
        )

    @staticmethod
    async def select_scheduled_emails(
        cursor: AsyncCursor[Any], timestamp: datetime
    ) -> AsyncCursor[Any]:
        return await cursor.execute(
            """
            SELECT
                id, created_at, last_updated_at, state, scheduled_at,
                to_header, from_header, reply_to_header, cc_header, bcc_header,
                subject, body, template_id
            FROM emails_scheduledemail
            WHERE
                (state = 'scheduled' OR state = 'failed')
                AND scheduled_at <= %s
            """,
            (timestamp,),
        )

    @staticmethod
    async def update_scheduled_email_status(
        cursor: AsyncCursor[Any], id: UUID, status: ScheduledEmailStatus
    ) -> AsyncCursor[Any]:
        return await cursor.execute(
            """
            UPDATE emails_scheduledemail SET state = %s WHERE id = %s
            """,
            (status.value, id),
        )

    @staticmethod
    async def insert_scheduled_email_log(
        cursor: AsyncCursor[Any],
        id: UUID,
        timestamp: datetime,
        details: str,
        state_before: ScheduledEmailStatus,
        state_after: ScheduledEmailStatus,
        scheduled_email_id: UUID,
    ) -> AsyncCursor[Any]:
        return await cursor.execute(
            """
            INSERT INTO emails_scheduledemaillog
            (id, created_at, details, state_before, state_after, scheduled_email_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                id,
                timestamp,
                details,
                state_before.value,
                state_after.value,
                scheduled_email_id,
            ),
        )


def read_database_credentials_from_ssm(stage: str) -> DatabaseCredentials:
    # TODO: turn into async
    database_host_parameter = read_ssm_parameter(f"/{stage}/amy/database_host")
    database_port_parameter = read_ssm_parameter(f"/{stage}/amy/database_port")
    database_name_parameter = read_ssm_parameter(f"/{stage}/amy/database_name")
    database_user_parameter = read_ssm_parameter(f"/{stage}/amy/database_user")
    database_password_parameter = read_ssm_parameter(f"/{stage}/amy/database_password")

    database_host = (
        get_parameter_value(database_host_parameter)
        if database_host_parameter
        else "localhost"
    )
    database_port = (
        get_parameter_value(database_port_parameter)
        if database_port_parameter
        else "5432"
    )
    database_name = (
        get_parameter_value(database_name_parameter)
        if database_name_parameter
        else "amy"
    )
    database_user = (
        get_parameter_value(database_user_parameter)
        if database_user_parameter
        else "fakeUser"
    )
    database_password = (
        get_parameter_value(database_password_parameter)
        if database_password_parameter
        else "fakePassword"
    )

    return DatabaseCredentials(
        HOST=database_host,
        PORT=database_port,
        USER=database_user,
        PASSWORD=database_password,
        NAME=database_name,
    )


def connection_string(credentials: DatabaseCredentials) -> str:
    return (
        f"postgresql://{credentials.USER}:{credentials.PASSWORD}"
        f"@{credentials.HOST}:{credentials.PORT}"
        f"/{credentials.NAME}"
    )


async def fetch_email_by_id(id: UUID, cursor: AsyncCursor[Any]) -> ScheduledEmail:
    await Db.select_scheduled_email(cursor, id)
    record = await cursor.fetchone()
    if not record:
        raise NotFoundError(f"Scheduled email {id} not found in DB")

    return ScheduledEmail(**record)


async def fetch_scheduled_emails_to_run(
    cursor: AsyncCursor[Any],
) -> list[ScheduledEmail]:
    now = datetime.now(tz=timezone.utc)
    await Db.select_scheduled_emails(cursor, timestamp=now)
    records = [ScheduledEmail(**record) for record in await cursor.fetchall()]
    return records


async def update_email_state(
    email: ScheduledEmail,
    new_state: ScheduledEmailStatus,
    cursor: AsyncCursor[Any],
    details: str = "State changed by worker",
) -> ScheduledEmail:
    now = datetime.now(tz=timezone.utc)
    id = email.id
    old_state = email.state
    await Db.update_scheduled_email_status(cursor, id, new_state)
    await Db.insert_scheduled_email_log(
        cursor, uuid4(), now, details, old_state, new_state, id
    )
    return await fetch_email_by_id(id, cursor)


async def lock_email(email: ScheduledEmail, cursor: AsyncCursor[Any]) -> ScheduledEmail:
    return await update_email_state(email, ScheduledEmailStatus.LOCKED, cursor)


async def fail_email(
    email: ScheduledEmail, details: str, cursor: AsyncCursor[Any]
) -> ScheduledEmail:
    return await update_email_state(
        email, ScheduledEmailStatus.FAILED, cursor, details=details
    )


async def succeed_email(
    email: ScheduledEmail, details: str, cursor: AsyncCursor[Any]
) -> ScheduledEmail:
    return await update_email_state(
        email, ScheduledEmailStatus.SUCCEEDED, cursor, details=details
    )
