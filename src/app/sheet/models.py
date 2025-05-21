from typing import Annotated, Final, Self

from gspread.worksheet import Worksheet
from pydantic import BaseModel, ConfigDict, field_validator


from ..shared.decorators import retry_on_fail
from .enums import CheckType
from .g_sheet import gsheet_client

COL_META: Final[str] = "col_name_xxx"
IS_UPDATE_META: Final[str] = "is_update_xxx"
IS_NOTE_META: Final[str] = "is_note_xxx"

INCLUDE_ROW_INDEX: Final[int] = 2
EXCLUDE_ROW_INDEX: Final[int] = 3
RELAX_ROW_INDEX: Final[int] = 2


class InExKeywordRelaxTime(BaseModel):
    include_keywords: dict[str, list[str] | None]
    exclude_keywords: dict[str, list[str] | None]
    relax_time: int


class ColSheetModel(BaseModel):
    # Model config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    sheet_id: str
    sheet_name: str
    index: int

    @classmethod
    def get_worksheet(
        cls,
        sheet_id: str,
        sheet_name: str,
    ) -> Worksheet:
        spreadsheet = gsheet_client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)

        return worksheet

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
                    if COL_META in metadata and IS_UPDATE_META in metadata:
                        mapping_fields[field_name] = metadata[COL_META]
                        break

        return mapping_fields

    @classmethod
    def get(
        cls,
        sheet_id: str,
        sheet_name: str,
        index: int,
    ) -> Self:
        mapping_dict = cls.mapping_fields()

        query_value = []

        for _, v in mapping_dict.items():
            query_value.append(f"{v}{index}")

        worksheet = cls.get_worksheet(sheet_id=sheet_id, sheet_name=sheet_name)

        model_dict = {
            "index": index,
            "sheet_id": sheet_id,
            "sheet_name": sheet_name,
        }

        query_results = worksheet.batch_get(query_value)
        count = 0
        for k, _ in mapping_dict.items():
            model_dict[k] = query_results[count].first()
            if isinstance(model_dict[k], str):
                model_dict[k] = model_dict[k].strip()
            count += 1
        return cls.model_validate(model_dict)

    @classmethod
    def batch_get(
        cls,
        sheet_id: str,
        sheet_name: str,
        indexes: list[int],
    ) -> list[Self]:
        worksheet = cls.get_worksheet(
            sheet_id=sheet_id,
            sheet_name=sheet_name,
        )
        mapping_dict = cls.mapping_fields()

        result_list: list[Self] = []

        query_value = []
        for index in indexes:
            for _, v in mapping_dict.items():
                query_value.append(f"{v}{index}")

        query_results = worksheet.batch_get(query_value)

        count = 0

        for index in indexes:
            model_dict = {
                "index": index,
                "sheet_id": sheet_id,
                "sheet_name": sheet_name,
            }

            for k, _ in mapping_dict.items():
                model_dict[k] = query_results[count].first()
                if isinstance(model_dict[k], str):
                    model_dict[k] = model_dict[k].strip()
                count += 1

            result_list.append(cls.model_validate(model_dict))
        return result_list

    @classmethod
    @retry_on_fail(max_retries=3, sleep_interval=30)
    def batch_update(
        cls,
        sheet_id: str,
        sheet_name: str,
        list_object: list[Self],
    ) -> None:
        worksheet = cls.get_worksheet(
            sheet_id=sheet_id,
            sheet_name=sheet_name,
        )
        mapping_dict = cls.updated_mapping_fields()
        update_batch = []

        for object in list_object:
            model_dict = object.model_dump(mode="json")

            for k, v in mapping_dict.items():
                update_batch.append(
                    {
                        "range": f"{v}{object.index}",
                        "values": [[model_dict[k]]],
                    }
                )

        if len(list_object) > 0:
            worksheet.batch_update(update_batch)

    @retry_on_fail(max_retries=3, sleep_interval=30)
    def update(
        self,
    ) -> None:
        mapping_dict = self.updated_mapping_fields()
        model_dict = self.model_dump(mode="json")

        worksheet = self.get_worksheet(
            sheet_id=self.sheet_id, sheet_name=self.sheet_name
        )

        update_batch = []
        for k, v in mapping_dict.items():
            update_batch.append(
                {
                    "range": f"{v}{self.index}",
                    "values": [[model_dict[k]]],
                }
            )

        worksheet.batch_update(update_batch)

    @classmethod
    @retry_on_fail(max_retries=5, sleep_interval=30)
    def update_note_message(
        cls,
        sheet_id: str,
        sheet_name: str,
        index: int,
        messages: str,
    ):
        for field_name, field_info in cls.model_fields.items():
            if hasattr(field_info, "metadata"):
                for metadata in field_info.metadata:
                    if COL_META in metadata and IS_NOTE_META in metadata:
                        worksheet = cls.get_worksheet(
                            sheet_id=sheet_id,
                            sheet_name=sheet_name,
                        )

                        worksheet.batch_update(
                            [
                                {
                                    "range": f"{metadata[COL_META]}{index}",
                                    "values": [[messages]],
                                }
                            ]
                        )


class Product(ColSheetModel):
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
    Relax: Annotated[
        int | None,
        {
            COL_META: "K",
        },
    ] = None

    @field_validator("price", "process_time", mode="before")
    def convert_to_str(cls, v):
        return str(v) if isinstance(v, (int, float)) else v

    @staticmethod
    @retry_on_fail(max_retries=5, sleep_interval=10)
    def get_run_indexes(sheet_id: str, sheet_name: str, col_index: int) -> list[int]:
        sheet = Product.get_worksheet(sheet_id=sheet_id, sheet_name=sheet_name)
        run_indexes = []
        check_col = sheet.col_values(col_index)
        for idx, value in enumerate(check_col):
            idx += 1
            if not isinstance(value, str):
                value = str(value)
            if value in [type.value for type in CheckType]:
                run_indexes.append(idx)

        return run_indexes

    @staticmethod
    def get_start_index() -> int:
        return 4

    @staticmethod
    @retry_on_fail(max_retries=10, sleep_interval=10)
    def get_include_exclude_keywords_mapping_relax_time(
        sheet_id: str, sheet_name: str
    ) -> InExKeywordRelaxTime:
        [include, exclude] = Product.batch_get(
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            indexes=[INCLUDE_ROW_INDEX, EXCLUDE_ROW_INDEX],
        )

        updated_mapping_fields = Product.updated_mapping_fields()

        include_dict = {
            k: [i.strip() for i in v.split(",")] if v else None
            for k, v in include.model_dump(mode="json").items()
            if k in updated_mapping_fields
        }

        exclude_dict = {
            k: [i.strip() for i in v.split(",")] if v else None
            for k, v in exclude.model_dump(mode="json").items()
            if k in updated_mapping_fields
        }

        return InExKeywordRelaxTime(
            include_keywords=include_dict,
            exclude_keywords=exclude_dict,
            relax_time=include.Relax if include.Relax else 3600,
        )

    @staticmethod
    @retry_on_fail(max_retries=10, sleep_interval=10)
    def clear_sheet(sheet_id: str, sheet_name: str, start_row: int) -> None:
        worksheet = Product.get_worksheet(sheet_id=sheet_id, sheet_name=sheet_name)
        # Fetch sheet dimensions
        total_rows = worksheet.row_count
        total_cols = worksheet.col_count

        # Helper to convert column index to letter (e.g., 1 -> 'A', 27 -> 'AA')
        def _col_idx_to_letter(idx: int) -> str:
            letters = ""
            while idx > 0:
                idx, rem = divmod(idx - 1, 26)
                letters = chr(65 + rem) + letters
            return letters

        end_col_letter = _col_idx_to_letter(total_cols)
        end_range = f"{end_col_letter}{total_rows}"  # e.g. 'Z1000'

        # Define A1 range to clear: from A{start_row} to end
        clear_range = f"A{start_row}:{end_range}"

        # Perform batch clear
        worksheet.batch_clear([clear_range])
