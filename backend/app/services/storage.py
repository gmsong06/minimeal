import json
import os
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

BACKEND_ROOT = Path(__file__).resolve().parents[2]
LOCAL_USERS_PATH = BACKEND_ROOT / "users.json"
LOCAL_MEAL_LOG_PATH = BACKEND_ROOT / "meal_log.json"

DEFAULT_USERS_TABLE = "minimeal-users"
DEFAULT_MEALS_TABLE = "minimeal-meals"

FAKE_ACCOUNTS: list[dict[str, str]] = [
    {
        "username": "minimeal_alex",
        "password": "minimeal123",
        "display_name": "Alex (Demo)",
    },
    {
        "username": "minimeal_riley",
        "password": "minimeal123",
        "display_name": "Riley (Demo)",
    },
    {
        "username": "minimeal_jordan",
        "password": "minimeal123",
        "display_name": "Jordan (Demo)",
    },
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StorageService:
    def __init__(self):
        self.storage_mode = os.getenv("MINIMEAL_STORAGE_MODE", "auto").lower()
        self.region_name = os.getenv("AWS_REGION", "us-east-1")
        self.users_table_name = os.getenv(
            "MINIMEAL_USERS_TABLE", DEFAULT_USERS_TABLE
        )
        self.meals_table_name = os.getenv(
            "MINIMEAL_MEALS_TABLE", DEFAULT_MEALS_TABLE
        )
        self.active_backend = "local"
        self._initialized = False
        self._dynamodb = None
        self._dynamodb_client = None
        self._users_table = None
        self._meals_table = None

    def initialize(self):
        if self._initialized:
            return

        prefer_dynamodb = self.storage_mode in {"auto", "dynamodb"}
        if prefer_dynamodb:
            try:
                self._initialize_dynamodb()
                self.active_backend = "dynamodb"
                self._initialized = True
                return
            except Exception:
                if self.storage_mode == "dynamodb":
                    raise

        self._initialize_local()
        self.active_backend = "local"
        self._initialized = True

    def list_seeded_accounts(self) -> list[dict[str, str]]:
        self.initialize()
        if self.active_backend == "dynamodb":
            accounts: list[dict[str, str]] = []
            for account in FAKE_ACCOUNTS:
                user = self._get_user_dynamodb(account["username"])
                if not user:
                    continue
                accounts.append(
                    {
                        "username": user["username"],
                        "password": user["password"],
                        "display_name": user.get(
                            "display_name", user["username"]
                        ),
                    }
                )
            return accounts

        return self._load_local_users()

    def authenticate(self, username: str, password: str) -> dict[str, str] | None:
        self.initialize()
        username = username.strip().lower()

        if self.active_backend == "dynamodb":
            user = self._get_user_dynamodb(username)
            if not user or user.get("password") != password:
                return None
            return {
                "username": user["username"],
                "display_name": user.get("display_name", user["username"]),
            }

        for user in self._load_local_users():
            if user["username"] == username and user["password"] == password:
                return {
                    "username": user["username"],
                    "display_name": user.get("display_name", user["username"]),
                }
        return None

    def user_exists(self, username: str) -> bool:
        self.initialize()
        username = username.strip().lower()

        if self.active_backend == "dynamodb":
            return self._get_user_dynamodb(username) is not None

        return any(user["username"] == username for user in self._load_local_users())

    def get_meals(self, username: str) -> list[dict[str, Any]]:
        self.initialize()
        username = username.strip().lower()

        if self.active_backend == "dynamodb":
            return self._get_meals_dynamodb(username)

        meals = [
            meal
            for meal in self._load_local_meals()
            if meal.get("username") == username
        ]
        meals.sort(key=lambda meal: meal.get("time_stamp", ""))
        return [self._sanitize_meal_item(meal) for meal in meals]

    def save_meal(self, username: str, meal_entry: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        username = username.strip().lower()

        if self.active_backend == "dynamodb":
            item = self._to_dynamodb_value({
                "username": username,
                **meal_entry,
                "updated_at": _utc_now_iso(),
            })
            self._meals_table.put_item(Item=item)
            return meal_entry

        meals = self._load_local_meals()
        meals.append({"username": username, **meal_entry, "updated_at": _utc_now_iso()})
        self._save_local_meals(meals)
        return meal_entry

    def delete_meal(self, username: str, meal_id: str) -> bool:
        self.initialize()
        username = username.strip().lower()

        if self.active_backend == "dynamodb":
            try:
                self._meals_table.delete_item(
                    Key={"username": username, "meal_id": meal_id},
                    ConditionExpression="attribute_exists(meal_id)",
                )
                return True
            except ClientError as exc:
                if (
                    exc.response.get("Error", {}).get("Code")
                    == "ConditionalCheckFailedException"
                ):
                    return False
                raise

        meals = self._load_local_meals()
        filtered_meals = [
            meal
            for meal in meals
            if not (
                meal.get("username") == username
                and str(meal.get("meal_id")) == meal_id
            )
        ]
        if len(filtered_meals) == len(meals):
            return False
        self._save_local_meals(filtered_meals)
        return True

    def set_meal_excluded_status(
        self, username: str, meal_id: str, excluded_from_daily_summary: bool
    ) -> dict[str, Any] | None:
        self.initialize()
        username = username.strip().lower()

        if self.active_backend == "dynamodb":
            try:
                response = self._meals_table.update_item(
                    Key={"username": username, "meal_id": meal_id},
                    UpdateExpression=(
                        "SET excluded_from_daily_summary = :excluded, "
                        "updated_at = :updated_at"
                    ),
                    ConditionExpression="attribute_exists(meal_id)",
                    ExpressionAttributeValues={
                        ":excluded": excluded_from_daily_summary,
                        ":updated_at": _utc_now_iso(),
                    },
                    ReturnValues="ALL_NEW",
                )
            except ClientError as exc:
                if (
                    exc.response.get("Error", {}).get("Code")
                    == "ConditionalCheckFailedException"
                ):
                    return None
                raise

            attrs = response.get("Attributes")
            if not attrs:
                return None
            return self._sanitize_meal_item(attrs)

        meals = self._load_local_meals()
        for meal in meals:
            if meal.get("username") != username or str(meal.get("meal_id")) != meal_id:
                continue
            meal["excluded_from_daily_summary"] = excluded_from_daily_summary
            meal["updated_at"] = _utc_now_iso()
            self._save_local_meals(meals)
            return self._sanitize_meal_item(meal)

        return None

    def _initialize_dynamodb(self):
        self._dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
        self._dynamodb_client = boto3.client(
            "dynamodb", region_name=self.region_name
        )
        self._ensure_table(
            table_name=self.users_table_name,
            key_schema=[{"AttributeName": "username", "KeyType": "HASH"}],
            attribute_definitions=[{"AttributeName": "username", "AttributeType": "S"}],
        )
        self._ensure_table(
            table_name=self.meals_table_name,
            key_schema=[
                {"AttributeName": "username", "KeyType": "HASH"},
                {"AttributeName": "meal_id", "KeyType": "RANGE"},
            ],
            attribute_definitions=[
                {"AttributeName": "username", "AttributeType": "S"},
                {"AttributeName": "meal_id", "AttributeType": "S"},
            ],
        )

        self._users_table = self._dynamodb.Table(self.users_table_name)
        self._meals_table = self._dynamodb.Table(self.meals_table_name)
        self._seed_accounts_dynamodb()

    def _ensure_table(
        self,
        table_name: str,
        key_schema: list[dict[str, str]],
        attribute_definitions: list[dict[str, str]],
    ):
        try:
            self._dynamodb_client.describe_table(TableName=table_name)
            return
        except self._dynamodb_client.exceptions.ResourceNotFoundException:
            pass

        tags = [
            {"Key": "Name", "Value": table_name},
            {"Key": "project", "Value": "minimeal"},
            {"Key": "managed-by", "Value": "minimeal-backend"},
        ]
        self._dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode="PAY_PER_REQUEST",
            Tags=tags,
        )
        waiter = self._dynamodb_client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)

    def _seed_accounts_dynamodb(self):
        now = _utc_now_iso()
        for account in FAKE_ACCOUNTS:
            try:
                self._users_table.put_item(
                    Item={
                        "username": account["username"],
                        "password": account["password"],
                        "display_name": account["display_name"],
                        "created_at": now,
                        "updated_at": now,
                    },
                    ConditionExpression="attribute_not_exists(username)",
                )
            except ClientError as exc:
                if (
                    exc.response.get("Error", {}).get("Code")
                    == "ConditionalCheckFailedException"
                ):
                    continue
                raise

    def _get_user_dynamodb(self, username: str) -> dict[str, Any] | None:
        response = self._users_table.get_item(Key={"username": username})
        return response.get("Item")

    def _get_meals_dynamodb(self, username: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        query_args: dict[str, Any] = {
            "KeyConditionExpression": Key("username").eq(username),
            "ScanIndexForward": True,
        }
        while True:
            response = self._meals_table.query(**query_args)
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
            query_args["ExclusiveStartKey"] = last_evaluated_key

        items.sort(key=lambda meal: meal.get("time_stamp", ""))
        return [self._sanitize_meal_item(meal) for meal in items]

    def _initialize_local(self):
        if not LOCAL_MEAL_LOG_PATH.exists():
            LOCAL_MEAL_LOG_PATH.write_text("[]", encoding="utf-8")

        if not LOCAL_USERS_PATH.exists():
            self._save_local_users(FAKE_ACCOUNTS)
            return

        local_users = self._load_local_users()
        by_username = {user["username"]: user for user in local_users}
        changed = False
        for account in FAKE_ACCOUNTS:
            if account["username"] in by_username:
                continue
            local_users.append(account)
            changed = True

        if changed:
            self._save_local_users(local_users)

    def _load_local_users(self) -> list[dict[str, str]]:
        if not LOCAL_USERS_PATH.exists():
            return []
        try:
            with open(LOCAL_USERS_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError):
            return []

        users: list[dict[str, str]] = []
        for row in data:
            username = str(row.get("username", "")).strip().lower()
            password = str(row.get("password", ""))
            if not username or not password:
                continue
            users.append(
                {
                    "username": username,
                    "password": password,
                    "display_name": str(
                        row.get("display_name", username)
                    ),
                }
            )
        return users

    def _save_local_users(self, users: list[dict[str, str]]):
        with open(LOCAL_USERS_PATH, "w", encoding="utf-8") as file:
            json.dump(users, file, indent=2)

    def _load_local_meals(self) -> list[dict[str, Any]]:
        if not LOCAL_MEAL_LOG_PATH.exists():
            return []
        try:
            with open(LOCAL_MEAL_LOG_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(data, list):
            return []
        return data

    def _save_local_meals(self, meals: list[dict[str, Any]]):
        with open(LOCAL_MEAL_LOG_PATH, "w", encoding="utf-8") as file:
            json.dump(meals, file, indent=2)

    def _sanitize_meal_item(self, meal: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in meal.items():
            if key in {"username", "updated_at"}:
                continue
            cleaned[key] = self._from_dynamodb_value(value)
        return cleaned

    def _to_dynamodb_value(self, value: Any) -> Any:
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, dict):
            return {
                key: self._to_dynamodb_value(nested_value)
                for key, nested_value in value.items()
            }
        if isinstance(value, list):
            return [self._to_dynamodb_value(item) for item in value]
        return value

    def _from_dynamodb_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._from_dynamodb_value(nested_value)
                for key, nested_value in value.items()
            }
        if isinstance(value, list):
            return [self._from_dynamodb_value(item) for item in value]
        if isinstance(value, Decimal):
            if value == value.to_integral_value():
                return int(value)
            return float(value)
        return value


_STORAGE = StorageService()


def get_storage() -> StorageService:
    return _STORAGE


def initialize_storage():
    _STORAGE.initialize()
