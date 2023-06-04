from utils.ssm import get_parameter_value, read_ssm_parameter
from utils.types import DatabaseCredentials


def read_database_credentials_from_ssm(stage: str) -> DatabaseCredentials:
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

    return {
        "host": database_host,
        "port": database_port,
        "name": database_name,
        "user": database_user,
        "password": database_password,
    }
