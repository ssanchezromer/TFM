from EUFunding import EUFunding
# from Fandit_7experts import Fandit
import time
import warnings
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*?Old MapAsync APIs are deprecated.*?")

start_time = time.time()
eu = EUFunding()
# --------
eu.start_crawling(force_update=False)
# eu.get_text_and_summary_from_links(force_update=False)
# eu.get_type_company_from_descriptions(force_update=False)
# eu.insert_full_text_from_links()
# --------
# calculate time to make all the process in minutes and seconds
elapsed_time = time.time() - start_time
minutes = elapsed_time // 60
seconds = elapsed_time % 60
print(f"Elapsed time: {minutes} minutes and {seconds} seconds")


# start_time = time.time()
# fandit = Fandit()
# fandit.start_crawling(force_update=True)
# elapsed_time = time.time() - start_time
# minutes = elapsed_time // 60
# seconds = elapsed_time % 60
# print(f"Elapsed time: {minutes} minutes and {seconds} seconds")