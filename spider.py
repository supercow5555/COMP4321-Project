import requests
from bs4 import BeautifulSoup

from datetime import datetime
import re
import collections

from string import punctuation

from io import StringIO
from html.parser import HTMLParser

import nltk
from nltk import pos_tag, word_tokenize
from nltk.corpus import stopwords
nltk.download('punkt')

from sqlitedict import SqliteDict
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

skiplist = []

import time


url2pageID = collections.OrderedDict()
pageID2Url = collections.OrderedDict()
word2wordID = collections.OrderedDict()
pageID2PageMeta = collections.OrderedDict()
parentLink2ChildLink = collections.OrderedDict()
invertedIndex = collections.OrderedDict()
forwardIndex = collections.OrderedDict()

############### PORTER STEMMING  ################

def updateM(word):
    vowel = 'aeiou'
    structure = []
    structureLength = 0
    m = 0
    for x in word:
        if x in vowel:
            if (len(structure) == 0) or (structure[-1] == 'c'):
                structure.append('v')
        elif (len(structure) == 0) or (structure[-1] == 'v'):
            structure.append('c')
    structureLength = len(structure)
        
    m = structureLength/2
    if m > 0:
        if (structure[0] == 'c') and (structure[-1] == 'v'):
            m = m - 1
        elif (structure[0] == 'c') or (structure[-1] == 'v'):
            m = m - 0.5
    return [structure, structureLength, m]

def check_cvcwxy(word):
    vowel = 'aeiou'
    if (len(word) >= 3) and (word[-1] not in (vowel or 'wxy')) and (word[-2] in vowel) and (word[-3] not in vowel):
            return True
    else:
        return False

def Porter(word):
    if (word.isalpha() == False):
        return word
    if len(word) < 3:
        return word
    else:
        vowel = 'aeiou'
        #structure = []
        #structureLength = 0
        #m = 0 
        
        update = updateM(word)
        
        #For 'fff' case
        if update[1] == 1:
            return word
        
        #Step 1a
        if word.endswith('sses'):
            word = word.replace('sses', 'ss')
        elif word.endswith('ies'):
            word = word.replace('ies', 'i')
        elif word.endswith('ss'):
            word = word
        elif word.endswith('s'):
            word = word.replace('s', '')
        
        #Step 1b
        nextStep = False
        temp = word
        if word.endswith('eed'):
            temp = word[0:-3]
            if updateM(temp)[2] > 0:
                word = word.replace('eed', 'ee')
        if 'v' in update[0][1:-1]:  
            if word.endswith('ed'):
                temp = word.replace('ed', '')
            elif word.endswith('ing'):
                temp = word.replace('ing', '')
            if temp != word:
                for x in temp:
                    if x in vowel:
                        word = temp
                        nextStep = True
        
        update = updateM(word)
        
        #Step 1b continued
        if nextStep == True:
            if word.endswith('at'):
                word = word.replace('at', 'ate')
            elif word.endswith('bl'):
                word = word.replace('bl', 'ble')
            elif word.endswith('iz'):
                word = word.replace('iz', 'ize')
            if len(word) < 2:
                return word
            elif (word[-1] == word[-2]) and (word[-1] not in 'lsz'):
                word = word[0:-1]
            elif (check_cvcwxy(word) == True) and (update[2] == 1):
                word = word + 'e'
        
        #Step 1c
        vowelExist = False
        for x in word:
            if x in vowel:
                vowelExist = True
        if (vowelExist == True) and (word.endswith('y') == True):
            word = word.replace('y', 'i')
        
        #Step 2
        Step2Dict = {'ational': 'ate',
                    'tional': 'tion',
                    'enci': 'ence',
                    'anci': 'ance',
                    'izer': 'ize',
                    'abli': 'able',
                    'alli': 'al',
                    'entli': 'ent',
                    'eli': 'e',
                    'oucli': 'ous',
                    'ization': 'ize',
                    'ation': 'ate',
                    'ator': 'ate',
                    'alism': 'al',
                    'iveness': 'ive',
                    'fulness': 'ful',
                    'ousness': 'ous',
                    'aliti': 'al',
                    'iviti': 'ive',
                    'biliti': 'ble'}
        temp = word
        for x in Step2Dict:
            if temp.endswith(x):
                temp = word.replace(x, '')
                if updateM(temp)[2] > 0:
                    word = word.replace(x, Step2Dict[x])
                    
        #Step 3
        Step3Dict = {'icate': 'ic',
                    'ative': '',
                    'alize': 'al',
                    'iciti': 'ic',
                    'ical': 'ic',
                    'ful': '',
                    'ness': ''}
        temp = word
        for x in Step3Dict:
            if temp.endswith(x):
                temp = word.replace(x, '')
                if updateM(temp)[2] > 0:
                    word = word.replace(x, Step3Dict[x])
        
        #Step 4
        Step4List = ['al', 'ance', 'ence', 'er', 'ic', 'able', 'ible', 'ant', 'ement', 'ment', 'ent', 
                     'ion', 'ou', 'ism', 'ate', 'iti', 'ous', 'ive', 'ize']
        for x in Step4List:
            if word.endswith(x):
                temp = word.replace(x, '')
                if x == 'ion':
                    if (temp.endswith('s') == True) or (temp.endswith('t') == True):
                        if updateM(temp[0:-1])[2] > 1:
                            word = word.replace(x, '')
                else:
                    if updateM(temp)[2] > 1:
                        word = word.replace(x, '')
        
        #Step 5a
        temp = word
        if temp.endswith('e'):
            temp = word[0:-1]
            m = updateM(temp)[2]
            if m > 1:
                word = temp
            if (m == 1) and (check_cvcwxy(temp) == False):
                word = temp
        
        #Step 5b
        if (word[-1] == 'l') and (word[-2] == 'l') and (updateM(word)[2] > 1):
            word = word[0:-1]
            
        return word

############### HELPER FUNCTIONS ################

def print_db(db):
    """
    To print out a database
    """
    for key, item in db.items():
        print("%s=%s" % (key, item))

def save2SqliteDict(dictionary_object, directory_location):
    """
    Save the contents of an ordered dictionary object to an SQLite database using the sqlitedict library.

    Args:
        dictionary_object (collections.OrderedDict): An ordered dictionary object containing the key-value pairs to be saved to the database.
        directory_location (str): A string representing the directory where the SQLite database will be saved.

    Returns:
        None

    Example usage:
        >>> url2pageID = collections.OrderedDict()
        >>> save2SqliteDict(url2pageID, 'database.db')
    """
    sqliteDict = SqliteDict(directory_location)
    print("Saving database to" + directory_location)
    i_max = len(dictionary_object) - 1
    i = 0
    for key, value in dictionary_object.items():
        print(directory_location, str(i), str(i_max))
        i += 1
        sqliteDict[key] = value
    sqliteDict.commit()
    sqliteDict.close()

def get_rawHTML(input_URL):
    """
    Retrieves the raw HTML of a URL.

    Args:
        input_URL: String of a URL

    Returns:
        Raw HTML in string for further parsing  
    
    Note: Doesn't verify certificate
    """
    response = requests.get(input_URL, verify=False)
    html_content = response.content
    return html_content

def get_links(str_HTML):
    """
    Extracts links in a given HTML String from finding the <a> tags in a

    Args: 
        str_HTML: Raw HTML content in a tring

    Returns: 
        All URLs in the raw HTML
    """
    bs_object = BeautifulSoup(str_HTML, 'html.parser')
    link_list = []

    for link in bs_object.findAll("a"):         # Find all <a> tags in the parsed HTML content
        href = link.get('href')
        if href is not None: # and href.startswith("http"):
            link_list.append(href)

    return link_list

def get_HTMLheaders(input_URL):
    response = requests.get(input_URL)
    headers = response.headers
    return headers

def get_displayedText(raw_html):
    """
    Retrieves all displayed text from a raw HTML string

    Args: 
        str_HTML: Raw HTML content in a tring

    Returns: 
        string: All displayed text of a webpages raw HTML in a string
    """
    bs_object = BeautifulSoup(raw_html, 'html.parser')
    displayed_text = bs_object.get_text()
    return displayed_text

def get_title(raw_html):
    """
    Retrieves the title of the webpage from a raw HTML string

    Args: 
        str_HTML: Raw HTML content in a tring

    Returns: 
        string: Title of the webpage
    """
    try:
        bs_object = BeautifulSoup(raw_html, 'html.parser')
        title_tag = bs_object.find("title")
        if title_tag is not None:
            page_title = title_tag.text
            return page_title
    except:
        return None

def get_metadata (raw_html):
    """
    Retrieves the date from a raw HTML string

    Args: 
        str_HTML: Raw HTML content in a tring

    Returns: 
        string: the date that is sometimes displayed in the <class: pull-right> in HKUST raw HTML pages, otherwise returns today's date
    """
    bs_object = BeautifulSoup(raw_html, 'html.parser')
    last_modified = datetime.now().strftime("%Y-%m-%d")
    try:
        pull_right_date = bs_object.find('span', {"class": "pull-right"})
        re_pattern = re.compile("\d+-\d+-\d+")
        last_modified = re.findall(re_pattern, pull_right_date.text)[0]
    except Exception:
        pass
    return last_modified
    ## Todo: Find more ways to extract date from different websites

def get_allwords(displayed_text):
    """
    Retrieves all induvidual words from a string

    Args: 
        displayed_text: str of all displayed text 

    Returns: 
        List: list of all keywords 
    """
    words = displayed_text.split()
    return words

def get_cleaned_and_filtered_kws(input_URL: str, stopwords: list[str]) -> list[str]:
    """
    Extracts keywords from the displayed text of a webpage specified by input_URL.

    Args:
        input_URL (str): the URL of the webpage to extract keywords from
        stopwords (list): a list of words to exclude from the extracted keywords

    Returns:
        list: a list of lowercased, alphanumeric keywords extracted from the displayed text of the webpage,
            with punctuation and empty strings removed and stopwords excluded
    """
    displayed_text = get_displayedText(get_rawHTML(input_URL))

    if not displayed_text:
        return 

    tokens = word_tokenize(displayed_text)
    # Change to lower case
    tokens = [word.lower() for word in tokens]

    # Remove punctuation
    table = str.maketrans('', '', punctuation)
    tokens = [w.translate(table) for w in tokens]

    # Remove non alpha-numeric
    tokens = [re.sub('[^A-Za-z0-9]+', '', w) for w in tokens]

    # Remove empty strings
    tokens = [w for w in tokens if w != '']

    # Remove stopwords
    tokens = [w for w in tokens if w not in stopwords]
    
    # Porter's function
    # tokens = [Porter(w) for w in tokens]
    tokens = [Porter(w) if len(w) >= 3 else w for w in tokens]
    return tokens

def get_dictKWS(filtered_words: list) -> dict[str, int]:
    """
    Converts list of keywords of a webpage into a dictionary which counts frequency of occurance

    Args:
        filtered_words: list of keywords

    Returns: 
        Dictionary: Dictionary of keywords and their frequency
    """
    
    if not filtered_words:
        return

    word_dict = {}

    for word in filtered_words:
        if word in word_dict:
            word_dict[word] += 1
        else:
            word_dict[word] = 1
    
    return word_dict

def sort_dict(word_dict):
    
    if not word_dict:
        return 
    
    sorted_dict = dict(sorted(word_dict.items(), key=lambda item: item[1], reverse=True))
    return sorted_dict

def get_size(input_URL: str) -> int:
    return len(get_rawHTML(input_URL))

############### PPUSHING TO DICTIONARY FUNCTIONS ################

def cleaned_and_filtered_kws_to_wordID(filtered_words: list, word2wordID: dict[str, int]) -> None:
    """
    Adds unique IDs to a dictionary of cleaned and filtered keywords.

    Args:
        filtered_words: A list of cleaned and filtered keywords.
        word2wordID: A dictionary that maps keywords to unique IDs.

    Returns:
        None.

    Modifies:
        The `word2wordID` dictionary is modified by adding new keyword-IDs mappings.

    Description:
        For each keyword in the `filtered_words` list, this function checks if the keyword is already a key in the `word2wordID` dictionary.
        If the keyword is not in the dictionary, a new key-value pair is added where the keyword is the key and a unique ID is the value.
        The unique ID is assigned by incrementing the length of the `word2wordID` dictionary.
    """
    
    # Ensure filtered_words is not empty
    if not filtered_words:
        return
    
    for current_word in filtered_words:
        if current_word not in word2wordID:

            # only if the word not in word2wordID, get the new wordID 
            current_word_ID = len(word2wordID)

            word2wordID[current_word] = current_word_ID

def push_to_invertedIndex(word_frequency: dict[str, int], pageID: int) -> None:
    """
    Update an inverted index data structure with the words and their frequencies from a given page.

    Args:
        word_frequency (dict[str, int]): A dictionary that maps words to their frequencies on the given page.
        pageID (int): An identifier for the page from which the words and frequencies are obtained.

    Returns:
        None: This function does not return a value.

    Notes:
        The inverted index is represented as a dictionary called `invertedIndex`, where the keys are word IDs 
        obtained from a separate dictionary called `word2wordID`, and the values are lists of tuples representing 
        the pages where the word appears and the frequency of the word in that page. If a word is not already in 
        the inverted index, a new entry is created with the current page and frequency. If a word is already in 
        the inverted index, the current page and frequency are appended to the existing list for that word.

    """
    
    if not word_frequency:
        return
    
    for word, freq in word_frequency.items():

        # Check: If word not in then make a new key-value, otherwise appended value to existing key
        if word2wordID[word] not in invertedIndex:
            invertedIndex[word2wordID[word]] = [(pageID, freq)]
        else:
            invertedIndex[word2wordID[word]].append((pageID, freq))

def push_to_forwardIndex(word_frequency: dict[str, int], pageID: int) -> None:
    # TODO: PageID -> {WordID, Freq}... Right now its {Word, Frequency}
    forwardIndex[pageID] = word_frequency

def push_to_childLink2ParentLink(pageID: int, child_links: list[str]) -> None:
    # NOTE: Consider making all parentIDs = -1 as a default value first
    # TODO: Assign parent-child relationship for visited/indexed children
    # TODO: Pre-assign parent-child relationship for children in queue
    parentLink2ChildLink[pageID] = child_links
    return

def push_to_pageID2PageMeta(pageID: int, page_title: str, last_date_modified: str, \
                            page_size: int, term_freq: dict[str:int], \
                            child_links: list[str]) -> None:
    pageID2PageMeta[pageID] = [page_title,
                               last_date_modified,
                               page_size,
                               term_freq,
                               child_links]
    return


############### MAIN FUNCTION ################

def BFS(input_URL, target):
    """
    Extracts webpages in a breadth-first search (BFS) manner starting from the input URL.

    Args:
        input_URL (str): The URL of the webpage to start the BFS from.
        target (int): The maximum number of webpages to extract in the BFS.

    Returns:
        None

    Example usage:
        >>> BFS("https://www.example.com", 50)
    

    The `BFS` function takes an input URL and a target number of webpages to extract, and performs a breadth-first search to extract the webpages. 
    It uses a queue to keep track of the webpages to extract, and a set to keep track of the webpages that have already been visited.

    The function iteratively extracts webpages from the queue, and for each webpage, it prints the URL, title, and metadata (last modified date). 
    It then extracts the child links of the webpage and adds them to the queue if they have not been visited before.

    The `BFS` function has no return value, as it simply prints the URLs, titles, and metadata of the extracted webpages to the console. 
    An example usage of the function is also provided in the docstring.
    """
    # Use the length of url2pageID ordered dictionary to act as the pageID to be assigned to URLs
    
    # TODO: Figure out why I can't set currentPageID as the length of the url2pageID, but idk if it matters anyway
    # currentPageID = len(url2pageID)
    currentPageID = 0
    # print('{}'.format(currentPageID), time.perf_counter())

    queue = []
    queue.append(input_URL)
    
    # TODO: Check URL -> PageID Doesn't exist in inverted index (WordID -> PageID)
    visited = set()
    visited.add(input_URL)

    # num_pages_indexed = 0
    while queue and currentPageID < target:
        current_url = queue.pop(0)
        # print("Post Pop:", time.perf_counter())
        print('{}'.format(currentPageID), time.perf_counter())

        # Skip links in Skip list
        if any(skip_url in current_url for skip_url in skiplist):
            continue

        # print("Post skip:", time.perf_counter())
        # Save to url2pageID and pageID2URL with currentPageID
        url2pageID[current_url] = currentPageID
        pageID2Url[currentPageID] = current_url

        # print("post save to url2pageID and pageID2URL with currentPageID:", time.perf_counter())
        # Save words to word2wordID dictionary
        cleaned_and_filtered_kws = get_cleaned_and_filtered_kws(current_url, stop_words)
        cleaned_and_filtered_kws_to_wordID(cleaned_and_filtered_kws, word2wordID)

        # print("post Save words to word2wordID dictionary:", time.perf_counter())
        # Inverted Index
        word_frequency_dict = sort_dict(get_dictKWS(cleaned_and_filtered_kws))
        push_to_invertedIndex(word_frequency_dict, url2pageID[current_url])

        # print("post: Inverted Index", time.perf_counter())
        # Forward Index
        push_to_forwardIndex(word_frequency_dict, url2pageID[current_url])

        # print("Forward Index:", time.perf_counter())
        # Parent-child relationship
        raw_html = get_rawHTML(current_url)
        child_links = get_links(raw_html)
        pattern = r"\.\./"
        push_to_childLink2ParentLink(url2pageID[current_url], [Base_URL + re.sub(pattern, "", link) for link in child_links])

        # print("post Parent-child relationship:", time.perf_counter())
        # PageID2PageMeta 
        page_title = get_title(raw_html)
        last_date_modified = get_metadata(raw_html)
        page_size = get_size(current_url)
        term_freq = sort_dict(get_dictKWS(get_cleaned_and_filtered_kws(current_url, stop_words)))
        push_to_pageID2PageMeta(url2pageID[current_url], page_title, last_date_modified, \
                                page_size, term_freq, child_links)

        # print("PageID2PageMeta:", time.perf_counter())
        # Checking
        print("Current Page ID:", url2pageID[current_url])
        print("URL:", pageID2Url[currentPageID])
        print("Title:", get_title(raw_html))
        print("Last modified:", get_metadata(raw_html))

        currentPageID += 1
        # print("post pageid+1:", time.perf_counter())
        # NOTE: This is not a recursive function, it is a while loop that calls the function get_links()
        # TODO: Change this to inverted index check
        for child in child_links:
            if child not in visited:
                visited.add(child)
                queue.append(Base_URL + child)

############################################################

# input_URL = 'https://cse.hkust.edu.hk'
input_URL = 'https://www.cse.ust.hk/~kwtleung/COMP4321/testpage.htm'
# input_URL = 'https://www.cse.ust.hk/~kwtleung/COMP4321/Movie.htm'
Base_URL = 'https://www.cse.ust.hk/~kwtleung/COMP4321/'

nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

############################################################


# print('_________________________')
# print(get_displayedText(get_rawHTML(input_URL)))
# print('_________________________')
# print(get_allwords(get_displayedText(get_rawHTML(input_URL))))
# print('_________________________')
# print(len(get_allwords(get_displayedText(get_rawHTML(input_URL)))))
# print('_________________________')
# print(get_cleaned_and_filtered_kws(input_URL, stop_words))
# print('_________________________')
# print(len(get_cleaned_and_filtered_kws(get_displayedText(get_rawHTML(input_URL)), stop_words)))
# print('_________________________')
# print(get_dictKWS(get_cleaned_and_filtered_kws(input_URL, stop_words)))
# print('_________________________')
# print(sort_dict(get_dictKWS(get_cleaned_and_filtered_kws(input_URL, stop_words))))
# print('_________________________')
# print(get_links(get_rawHTML(input_URL)))
# print('_________________________')
# print(len(get_links(get_rawHTML(input_URL))))
# print('_________________________')
# print((get_rawHTML(input_URL)))
BFS(input_URL, 300)
# print_db(word2wordID)
# print_db(invertedIndex)
# print_db(forwardIndex)
# print_db(parentLink2ChildLink)
# print_db(pageID2PageMeta)




############################################################

save2SqliteDict(url2pageID, 'website/db/url2pageID.sqlite')
save2SqliteDict(pageID2Url, 'website/db/pageID2Url.sqlite')
save2SqliteDict(pageID2PageMeta, 'website/db/pageID2PageMeta.sqlite')
save2SqliteDict(invertedIndex, 'website/db/invertedIndex.sqlite')
save2SqliteDict(forwardIndex, 'website/db/forwardIndex.sqlite')
save2SqliteDict(parentLink2ChildLink, 'website/db/parentLink2ChildLink.sqlite')



