# from app.lpk.api_client import lpk_api_client


# print(lpk_api_client.get_all_products())

# from app import config
# from app.sheet.models import Product

# print(
#     Product.get_include_exclude_keywords_mapping_relax_time(
#         config.SPREADSHEET_KEY, config.SHEET_NAME
#     )
# )
from app.processes import process

process()
