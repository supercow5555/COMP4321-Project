from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re

from string import punctuation

import nltk
from nltk import pos_tag, word_tokenize
from nltk.corpus import stopwords
nltk.download('punkt')
################ Retrieval Function script ################

from sqlitedict import SqliteDict
import math

url2pageID = SqliteDict('db/url2pageID.sqlite')
pageID2Url = SqliteDict('db/pageID2Url.sqlite')
pageID2PageMeta = SqliteDict('db/pageID2PageMeta.sqlite')
invertedIndex = SqliteDict('db/invertedIndex.sqlite')
forwardIndex = SqliteDict('db/forwardIndex.sqlite')
parentLink2ChildLink = SqliteDict('db/parentLink2ChildLink.sqlite')

################ Clean Query Function ################

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
    displayed_text = input_URL

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

nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

################ Retrieval Function script ################

def print_db(db):
    """
    To print out a database
    """
    for key, item in db.items():
        print("%s=%s" % (key, item))

def Query2Dict(query: list) -> dict[str:int]:
    """
    This function takes a string as input and outputs a dictionary with keys as words and values as the frequency of 
    occurrence of each word in the input string.
    
    Args:
        query: A string input for which we want to create a dictionary of word frequency.
        
    Returns:
        A dictionary containing the frequency of each word in the input string.
    """
    # Convert the input string to lowercase and split it into a list of words
    # words = query.lower().split()
    words = query
    
    # Create an empty dictionary to hold the frequency of each word
    word_frequency = {}
    
    # Iterate through each word in the list of words
    for word in words:
        
        # If the word is already in the dictionary, increment its count
        if word in word_frequency:
            word_frequency[word] += 1
        
        # If the word is not yet in the dictionary, add it with a count of 1
        else:
            word_frequency[word] = 1

    # Return the dictionary of word frequency
    return word_frequency

def TF_Collection_Builder() -> list[dict[str:int]]:
    """
    Builds a collection of term frequency dictionaries for all pages in pageID2PageMeta.

    Returns:
    --------
    list[dict[str:int]]: A list of term frequency dictionaries for each page in pageID2PageMeta.
    """
    TF_Collection = []

    # Iterating over each page in pageID2PageMeta
    for pageID in range(len(pageID2PageMeta)):
        # Extracting the term frequency dictionary of the page
        Page_TF = pageID2PageMeta[pageID][3]
        # Appending the term frequency dictionary of the page to the TF_Collection list
        TF_Collection.append(Page_TF)
    
    # Returning the TF_Collection list
    return TF_Collection 

def IDF_Collection_Builder(TF_Collection: list[dict[str:int]], log_base: int) -> dict[str:int]:
    """
    This function takes in a collection of term frequency and builds an inverse document frequency (IDF) collection.
    
    Parameters:
        TF_Collection list[dict[str:int]]: A list of term frequency dictionaries for each page in pageID2PageMeta.
        log_base (int): Base of logarithm to be used for IDF calculation.
    
    Returns:
        IDF_Collection (dict): A dictionary containing IDF values for each unique term in the collection.
    """
    # initialize empty dictionaries
    DF_Collection = {}
    IDF_Collection = {}

    # count total number of documents in collection
    number_of_documents = len(TF_Collection)

    # iterate through each document in the collection

    for pageID in TF_Collection:
        # iterate through each word in the document
        for word in pageID:
            # increment document frequency and IDF values if word already exists in dictionaries
            try:
                DF_Collection[word] += 1
                IDF_Collection[word] += 1
            # create new entries in dictionaries if word is not already present
            except:
                DF_Collection[word] = 1
                IDF_Collection[word] = 1
            
            # calculate IDF value for the current word and store it in IDF_Collection dictionary
            IDF_Collection[word] = math.log((number_of_documents/IDF_Collection[word]), log_base)
    return IDF_Collection

def TF_IDF_Collection_Builder(TF_Collection: list[dict[str:int]], IDF_Collection: dict[str:int]) -> list[dict[str:int]]:
    """
    Calculate the TF-IDF score for each word in a collection of documents.

    Parameters:
    -----------
    TF_Collection : list[dict[str:int]]
        A list of dictionaries where each dictionary contains the term frequency of each word in a document.
    IDF_Collection : dict[str:int]
        A dictionary containing the inverse document frequency of each word in the entire collection.

    Returns:
    --------
    list[dict[str:int]]
        A list of dictionaries where each dictionary contains the TF-IDF score of each word in a document.
    """
    TF_IDF_Collection = []

    # iterate over each document in the collection
    for TF_Document in TF_Collection:

        max_tf = max(TF_Document.values())

        TF_IDF_Page = {}
        # iterate over each word in the document
        for word in TF_Document:
            # calculate the TF-IDF score of the word in the document
            # TODO: Normalize it here probably
            TF_IDF_Page[word] = (TF_Document[word]/max_tf) * IDF_Collection[word]
        # append the TF-IDF scores of all the words in the document to the TF-IDF collection
        TF_IDF_Collection.append(TF_IDF_Page)

    return TF_IDF_Collection

def CoSinSim_Document(TF_IDF_Collection: list[dict[str:int]], query_dict:dict[str:int], pageID: int) -> float:
    """
    Computes the cosine similarity between a given document and a query using their TF-IDF scores.

    Parameters:
    TF_IDF_Collection (list[dict[str:int]]): A list of dictionaries where each dictionary contains the TF-IDF scores of a document.
    query_dict (dict[str:int]): A dictionary where keys are words in the query and values are their term frequency.
    pageID (int): The ID of the document in the collection.

    Returns:
    float: The cosine similarity between the document and the query.
    """
    # Calculate the dot product between the query and the document
    dot_product = 0.0
    for word in query_dict:
        try: 
            dot_product += query_dict[word] * TF_IDF_Collection[pageID][word]
        except:
            pass

    # Calculate the length of the query
    query_length = 0.0
    for word in query_dict:
        query_length += query_dict[word]**2
    query_length **= 0.5

    # Calculate the length of the document
    page_length = 0.0
    for word in TF_IDF_Collection[pageID]:
        page_length += TF_IDF_Collection[pageID][word]**2
    page_length **= 0.5

    # TODO: Temporary solution is that if page doesn't have any contents, make it score = 0, 
    # but why does the page not have any contents in the first place?

    # check for zero query or page length before division
    if query_length == 0 or page_length == 0:
        return 0  # or any other default value or error handling

    # Return the cosine similarity between the document and the query
    return dot_product/(query_length*page_length)

def CoSinSim_AllDocuments(TF_IDF_Collection: list[dict[str:int]], query_dict:dict[str:int], \
                          number_of_pages: int) -> dict[int:int]:
    CoSinDict = {}
    for pageID in range(number_of_pages):
        CoSinDict[pageID] = CoSinSim_Document(TF_IDF_Collection, query_dict, pageID)

    return CoSinDict

def Sort_CoSinSim_AllDocuments(CoSimSim_AllDocuments: dict[int:int]) -> dict[int:int]:
    sortedCosSimDict = {k: v for k, v in sorted(CoSimSim_AllDocuments.items(), key=lambda item: item[1], reverse=True)}
    return sortedCosSimDict

def Retrieve_URL_From_Dict(Sorted_CoSinSim_AllDocuments: dict[int:int], pageID2Url: dict[int:str]) -> dict[int:(float, str)]:
    # Init list
    full_output = []


    # loop through the sorted cosine similarity values for each page
    for page_id in Sorted_CoSinSim_AllDocuments:
        # initialize an empty dictionary to store the ranked urls
        one_output = {}

        # get the url associated with the page id from the pageID2Url dictionary
        url = pageID2Url.get(page_id)

        # top 5 TF list

        top5 = list((pageID2PageMeta[page_id][3]).items())[:5]
        child5 = parentLink2ChildLink[page_id][:5]
        
        # parent = []
        # for key, value in parentLink2ChildLink.items():
        #     if value == pageID2Url[page_id]:
        #         parent.append(key)

        one_output[Sorted_CoSinSim_AllDocuments[page_id]] = [pageID2PageMeta[page_id][0], url, \
                                                                pageID2PageMeta[page_id][1], pageID2PageMeta[page_id][2], \
                                                                top5, child5]
        full_output.append(one_output)

    # return the list of ranked results
    return full_output

def RunQuery(query: str) -> dict:
    clean_query = get_cleaned_and_filtered_kws(query, stop_words)
    query_dict = Query2Dict(clean_query)
    TF_Collection = TF_Collection_Builder()
    IDF_Collection = IDF_Collection_Builder(TF_Collection, 2)
    TF_IDF_Collection = TF_IDF_Collection_Builder(TF_Collection, IDF_Collection)

    # Running Query against all pages
    number_of_pages = len(TF_Collection)

    CoSinDict = CoSinSim_AllDocuments(TF_IDF_Collection, query_dict, number_of_pages)

    Sorted_CoSinSim_AllDocuments = Sort_CoSinSim_AllDocuments(CoSinDict)
    Ranked_URLs = Retrieve_URL_From_Dict(Sorted_CoSinSim_AllDocuments, pageID2Url)

    # TODO: Normalize TF_IDF By max(TF) of that document

    return Ranked_URLs
# query = "hkust professor hong kong"
# RunQuery(query)

################ Web APP script ################
app = FastAPI(debug=True)

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:3000",
    "http://10.89.3.204:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Welcome to my search engine"}

@app.get("/query/")
async def query_endpoint(query: str):
    result_dict = RunQuery(query)
    print(result_dict)
    return result_dict


# /query/?query=Who%20is%20professor

# TODO: Title 
# TODO: Bigram phrase
# TODO: parent link