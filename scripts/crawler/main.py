from EUFunding import EUFunding
# from Fandit_7experts import Fandit
import time

start_time = time.time()
eu = EUFunding()
# --------
# eu.start_crawling(force_update=False)
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