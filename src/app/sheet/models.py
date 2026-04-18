from datetime import datetime

from typing import Annotated, Final, Self, TypeVar, Generic, Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from . import async_sheets_client
from .exceptions import SheetError
from ..utils import formated_datetime

T = TypeVar("T")

COL_META: Final[str] = "col_name_xxx"
IS_UPDATE_META: Final[str] = "is_update_xxx"
IS_NOTE_META: Final[str] = "is_note_xxx"


class NoteMessageUpdatePayload(BaseModel):
    index: int
    message: str


class BatchCellUpdatePayload(BaseModel, Generic[T]):
    cell: str
    value: T


class ColSheetModel(BaseModel):
    # Model config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    sheet_id: str
    sheet_name: str
    index: int

    @classmethod
    def mapping_fields(cls) -> dict:
        mapping_fields = {}
        for field_name, field_info in cls.model_fields.items():
            if hasattr(field_info, "metadata"):
                for metadata in field_info.metadata:
                    if COL_META in metadata:
                        mapping_fields[field_name] = metadata[COL_META]
                        break

        return mapping_fields

    @classmethod
    def updated_mapping_fields(cls) -> dict:
        mapping_fields = {}
        for field_name, field_info in cls.model_fields.items():
            if hasattr(field_info, "metadata"):
                for metadata in field_info.metadata:
                    if (
                        COL_META in metadata
                        and IS_UPDATE_META in metadata
                        and metadata[IS_UPDATE_META]
                    ):
                        mapping_fields[field_name] = metadata[COL_META]
                        break

        return mapping_fields

    @classmethod
    async def get(
        cls,
        sheet_id: str,
        sheet_name: str,
        index: int,
    ) -> Self:
        mapping_dict = cls.mapping_fields()
        ranges = [f"{sheet_name}!{col}{index}" for _, col in mapping_dict.items()]

        response = await async_sheets_client.batch_get(sheet_id, ranges)
        value_ranges = response.get("valueRanges", [])

        model_dict = {
            "index": index,
            "sheet_id": sheet_id,
            "sheet_name": sheet_name,
        }

        for i, (field_name, _) in enumerate(mapping_dict.items()):
            raw = (
                value_ranges[i].get("values", [[None]])
                if i < len(value_ranges)
                else [[None]]
            )
            val = raw[0][0] if raw and raw[0] else None
            if isinstance(val, str):
                val = val.strip()
            model_dict[field_name] = val

        return cls.model_validate(model_dict)

    @classmethod
    async def batch_get(
        cls,
        sheet_id: str,
        sheet_name: str,
        indexes: list[int],
    ) -> list[Self]:
        mapping_dict = cls.mapping_fields()

        result_list: list[Self] = []
        error_list: list[NoteMessageUpdatePayload] = []

        ranges = []
        for index in indexes:
            for _, col in mapping_dict.items():
                ranges.append(f"{sheet_name}!{col}{index}")

        response = await async_sheets_client.batch_get(sheet_id, ranges)
        value_ranges = response.get("valueRanges", [])

        count = 0

        for index in indexes:
            model_dict = {
                "index": index,
                "sheet_id": sheet_id,
                "sheet_name": sheet_name,
            }

            for field_name, _ in mapping_dict.items():
                raw = (
                    value_ranges[count].get("values", [[None]])
                    if count < len(value_ranges)
                    else [[None]]
                )
                val = raw[0][0] if raw and raw[0] else None
                if isinstance(val, str):
                    val = val.strip()
                model_dict[field_name] = val
                count += 1

            try:
                result_list.append(cls.model_validate(model_dict))
            except ValidationError as e:
                error_list.append(
                    NoteMessageUpdatePayload(
                        index=index,
                        message=f"{formated_datetime(datetime.now())} Validation Error at row {index}: {e.errors(include_url=False)}",
                    )
                )

        await cls.batch_update_note_message(
            sheet_id=sheet_id, sheet_name=sheet_name, update_payloads=error_list
        )

        return result_list

    @classmethod
    async def batch_update(
        cls,
        sheet_id: str,
        sheet_name: str,
        list_object: list[Self],
    ) -> None:
        mapping_dict = cls.updated_mapping_fields()
        update_batch = []

        for object in list_object:
            model_dict = object.model_dump(mode="json")

            for k, v in mapping_dict.items():
                update_batch.append(
                    {
                        "range": f"{sheet_name}!{v}{object.index}",
                        "values": [[model_dict[k]]],
                    }
                )

        if len(list_object) > 0:
            await async_sheets_client.batch_update(sheet_id, update_batch)

    async def update(
        self,
    ) -> None:
        mapping_dict = self.updated_mapping_fields()
        model_dict = self.model_dump(mode="json")

        update_batch = []
        for k, v in mapping_dict.items():
            update_batch.append(
                {
                    "range": f"{self.sheet_name}!{v}{self.index}",
                    "values": [[model_dict[k]]],
                }
            )

        await async_sheets_client.batch_update(self.sheet_id, update_batch)

    @classmethod
    async def update_note_message(
        cls,
        sheet_id: str,
        sheet_name: str,
        index: int,
        messages: str,
    ):
        for field_name, field_info in cls.model_fields.items():
            if hasattr(field_info, "metadata"):
                for metadata in field_info.metadata:
                    if (
                        COL_META in metadata
                        and IS_NOTE_META in metadata
                        and metadata[IS_NOTE_META]
                    ):
                        await async_sheets_client.batch_update(
                            sheet_id,
                            [
                                {
                                    "range": f"{sheet_name}!{metadata[COL_META]}{index}",
                                    "values": [[messages]],
                                }
                            ],
                        )
                        return

        raise SheetError("Can't update sheet message")

    @classmethod
    async def batch_update_note_message(
        cls,
        sheet_id: str,
        sheet_name: str,
        update_payloads: list[NoteMessageUpdatePayload],
    ):
        if not update_payloads:
            return

        for field_name, field_info in cls.model_fields.items():
            if hasattr(field_info, "metadata"):
                for metadata in field_info.metadata:
                    if (
                        COL_META in metadata
                        and IS_NOTE_META in metadata
                        and metadata[IS_NOTE_META]
                    ):
                        batch: list[dict] = []
                        for payload in update_payloads:
                            batch.append(
                                {
                                    "range": f"{sheet_name}!{metadata[COL_META]}{payload.index}",
                                    "values": [[payload.message]],
                                }
                            )
                        await async_sheets_client.batch_update(sheet_id, batch)
                        return

        # No note field defined on this model — silently skip rather than crash the batch
        return

    @classmethod
    async def free_style_batch_update(
        cls,
        sheet_id: str,
        sheet_name: str,
        update_payloads: list[BatchCellUpdatePayload],
    ):
        batch: list[dict] = []
        for payload in update_payloads:
            batch.append(
                {
                    "range": f"{sheet_name}!{payload.cell}",
                    "values": [[payload.value]],
                }
            )

        await async_sheets_client.batch_update(sheet_id, batch)


class RowModel(ColSheetModel):
    Code_Prefix: Annotated[
        str | None,
        {
            COL_META: "A",
        },
    ] = None
    GAME: Annotated[
        str | None,
        {
            COL_META: "C",
        },
    ] = None
    PACK: Annotated[
        str | None,
        {
            COL_META: "D",
        },
    ] = None
    code: Annotated[
        str | None,
        {
            COL_META: "E",
            IS_UPDATE_META: True,
        },
    ] = None
    country_code_priority: Annotated[
        str | None,
        {
            COL_META: "F",
        },
    ] = None
    LOWEST_PRICE: Annotated[
        str | None,
        {
            COL_META: "G",
            IS_UPDATE_META: True,
        },
    ] = None
    NOTE: Annotated[
        str | None,
        {
            COL_META: "H",
            IS_UPDATE_META: True,
            IS_NOTE_META: True,
        },
    ] = None
    LOG_CODE: Annotated[
        str | None,
        {
            COL_META: "I",
            IS_UPDATE_META: True,
        },
    ] = None
    LOG_COUNTRY: Annotated[
        str | None,
        {
            COL_META: "J",
            IS_UPDATE_META: True,
        },
    ] = None

    @classmethod
    async def get_run_indexes(cls, sheet_id: str, sheet_name: str) -> list[int]:
        """Get row indexes where col A has a non-empty value.

        Args:
            sheet_id: The spreadsheet ID
            sheet_name: The sheet name

        Returns:
            List of 1-based row indexes
        """
        rows = await async_sheets_client.get_column_values(sheet_id, sheet_name, "A")
        run_indexes = []
        for idx, row in enumerate(rows, start=1):
            value = row[0] if row else ""
            if not isinstance(value, str):
                value = str(value)
            if value.strip():
                run_indexes.append(idx)
        return run_indexes


class ListingRowModel(ColSheetModel):
    CHECK: Annotated[
        str | None,
        {
            COL_META: "A",
        },
    ] = None
    code: Annotated[
        str | None,
        {
            COL_META: "B",
            IS_UPDATE_META: True,
        },
    ] = None
    category_code: Annotated[
        str | None,
        {
            COL_META: "C",
            IS_UPDATE_META: True,
        },
    ] = None
    name: Annotated[
        str | None,
        {
            COL_META: "D",
            IS_UPDATE_META: True,
        },
    ] = None
    provider_code: Annotated[
        str | None,
        {
            COL_META: "E",
            IS_UPDATE_META: True,
        },
    ] = None
    price: Annotated[
        str | None,
        {
            COL_META: "F",
            IS_UPDATE_META: True,
        },
    ] = None
    process_time: Annotated[
        str | None,
        {
            COL_META: "G",
            IS_UPDATE_META: True,
        },
    ] = None
    country_code: Annotated[
        str | None,
        {
            COL_META: "H",
            IS_UPDATE_META: True,
        },
    ] = None
    status: Annotated[
        str | None,
        {
            COL_META: "I",
            IS_UPDATE_META: True,
        },
    ] = None
    Note: Annotated[
        str | None,
        {
            COL_META: "J",
            IS_UPDATE_META: True,
            IS_NOTE_META: True,
        },
    ] = None

    @field_validator("price", "process_time", mode="before")
    @classmethod
    def convert_to_str(cls, v: object) -> str | None:
        if isinstance(v, (int, float)):
            return str(v)
        return v  # type: ignore[return-value]
