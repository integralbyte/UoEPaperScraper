import requests
import math
from lxml import html
import time
import os
import re


def getTotalPageCount(pageHTML):
    elementXPath = '//*[@id="aspect_discovery_SimpleSearch_div_search"]/div[2]/div/div[1]/p[1]//text()'
    XPathTextList = pageHTML.xpath(elementXPath)
    XPathText = ''.join(XPathTextList)
    startIndex = XPathText.find("of")

    totalPages = int(XPathText[startIndex + 2:].strip())
    return totalPages

def getPaperName(pageHTML, div):
    elementXPath = f'//*[@id="aspect_discovery_SimpleSearch_div_search-results"]/div[{div}]/div/div[1]/a/h4//text()'
    elementResit = f'//*[@id="aspect_discovery_SimpleSearch_div_search-results"]/div[{div}]/div/div[1]/p'
    resitTextList = pageHTML.xpath(elementResit)
    XPathTextList = pageHTML.xpath(elementXPath)
    XPathText = ''.join(XPathTextList)
    if resitTextList:
        XPathText += " Resit"
    return XPathText

def getPaperURL(pageHTML, div):
    elementXPath = f'//*[@id="aspect_discovery_SimpleSearch_div_search-results"]/div[{div}]/div/div[2]/span[5]/small/a/@href'
    XPathHrefList = pageHTML.xpath(elementXPath)
    XPathHref = ''.join(XPathHrefList)
    
    return "https://exampapers.ed.ac.uk" + XPathHref

def getPapers(cookieName, cookieValue, courseID):
    searchResultsURL = searchResultsURL = f"https://exampapers.ed.ac.uk/discover?rpp=100&etal=0&group_by=none&page=1&filtertype_0=identifier&filter_relational_operator_0=equals&filter_0={courseID}"

    searchResponse = requests.get(searchResultsURL, cookies=searchResultsCookies)

    if "produced no results" in (searchResponse.text):
        raise Exception("Invalid Course ID! Please contact me at @integralbyte on Github if you believe this is an error.")
    
    searchHTML = html.fromstring(searchResponse.content)
    totalPageCount = math.ceil(getTotalPageCount(searchHTML)/100)
    i = 1
    papers = {}

    while i <= totalPageCount:
        searchResultsURL = f"https://exampapers.ed.ac.uk/discover?rpp=100&etal=0&group_by=none&page={i}&filtertype_0=identifier&filter_relational_operator_0=equals&filter_0={courseID}"
        searchResponse = requests.get(searchResultsURL, cookies=searchResultsCookies)
        searchHTML = html.fromstring(searchResponse.content)

        divs = searchHTML.xpath('//*[@id="aspect_discovery_SimpleSearch_div_search-results"]/div')
        divsCount = len(divs)

        for j in range(1, divsCount+1):
            paperName = getPaperName(searchHTML, j)
            paperURL = getPaperURL(searchHTML, j)
            papers[paperName] = paperURL
            
        i+=1
    
    return papers


CourseID = input("Course ID: ").upper()
cookieName = input("Complete ed.ac.uk cookie name starting with \"_shibsession\": ")
cookieValue = input("Value of the cookie: ")

print("\nExtracting Papers Data.")

searchResultsCookies = cookies = {
        cookieName: cookieValue
        }

papersDict = getPapers("a", "b", CourseID)

now = int(time.time())

folder_name = CourseID + " Exam Papers " + str(now)
os.mkdir(folder_name)

logsPath = os.path.join(folder_name, "logs.txt")

open(logsPath, "w").close()
print("Found " + len(papersDict) + " Papers! Download Started.")

success = 0
unavailable = 0
unknown = 0

for key, value in papersDict.items():

    if "unavailable" in value:
        with open(logsPath, "a") as f:
            f.write("Download Failed (Paper Unavailable): " + key + "\n")
            unavailable+=1
    elif ".pdf" in value:
        pdfResponse = requests.get(value, cookies=searchResultsCookies)
        safe_key = re.sub(r'[<>:"/\\|?*]', '_', key)
        pdfPath = os.path.join(folder_name, safe_key + ".pdf")

        with open(pdfPath, "wb") as f:
            f.write(pdfResponse.content)

        with open(logsPath, "a") as f:
            f.write("Download Successful: " + key + "\n")

            success+=1
    else:
        with open(logsPath, "a") as f:
            f.write("Download Failed (Unknown Error): " + key + ". Download URL: " + value + "\n")
            unknown+=1

if unknown == 0:
    print(f"Download Finished.\nOut of {len(papersDict)} found papers, {success} were downloaded successfully, {unavailable} were unavailable.")
else:
    print(f"Download Finished.\nOut of {len(papersDict)} found papers, {success} were downloaded successfully, {unavailable} were unavailable and {unknown} failed due to unknown reasons (check logs).")


full_path = os.path.abspath(folder_name)
print("Papers saved at: " + full_path)

