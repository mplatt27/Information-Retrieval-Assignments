"""
 Indexer
 Melanie Platt
 2-12-2021
 CS 6200 Information Retrieval
 Homework 1

 Sources:
 - https://elasticsearch-py.readthedocs.io/en/7.10.0/api.html
 - https://kb.objectrocket.com/elasticsearch/use-python-to-index-files-into-elasticsearch-index-all-files-in-a-directory-part-2-852
 - https://www.elastic.co/webinars/getting-started-elasticsearch?baymax=rtp&elektra=home&storm=sub2
 - https://kb.objectrocket.com/elasticsearch/how-to-create-and-delete-elasticsearch-indexes-using-the-python-client-library
 - https://qbox.io/blog/elasticsearch-algorithmic-stemming-tutorial
"""

import glob
import os
import re
import sys
from elasticsearch import Elasticsearch, helpers

# PART 1: CREATE ELASTIC SEARCH INDEX
# configure elastic search
config = {
    'host': '0.0.0.0'
}
es = Elasticsearch()

# Standard body of the index, used to create the index in ES
request_body = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "analysis": {
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords_path": 'my_stoplist.txt'
                },
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                }

            },
            "analyzer": {
                "stopped": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "english_stop",
                        "english_stemmer"
                    ]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "text": {
                "type": "text",
                "fielddata": True,
                "analyzer": "stopped",
                "index_options": "positions"
            }
        }
    }
}

# this creates ap_dataset in ES, using the request_body from above
# if it already exists, delete and make a new one, else create the new one
if es.indices.exists(index='ap_dataset'):
    deleted = es.indices.delete(index='ap_dataset', ignore=400)
    print("Previous index of the same name deleted, new version being created...")
    response = es.indices.create(index='ap_dataset', body=request_body, ignore=400)
    print(response)
else:
    response = es.indices.create(index='ap_dataset', body=request_body, ignore=400)
    print(response)


# PART 2: ADD DOCS TO INDEX
# next functions are used to parse the documents and add them to ES


# Function: get_files_in_dir()
# Input: folder_path: a path to a folder of files to be indexed
# Returns: file_path_list: a list of paths to each file in the folder
# Does: Gets the names of all files in the folder then appends each
# file's path name to a list to return
def get_files_in_dir(folder_path):
    # gets all names of files in directory
    file_list = os.listdir(folder_path)

    # append them to list with their full paths
    file_path_list = []
    for file in file_list:
        file_path_list.append(os.path.join(folder_path, file))

    return file_path_list


# Function: get_data_from_text_file()
# Input: file: a single file that may contain multiple documents to be indexed
# Returns: data: a list of lists; each sub-list is a line from the file
# Does: reads each line of the file and appends it in a list to data
def get_data_from_text_file(file):
    # declare an empty list for the data
    data = []
    for line in open(file, encoding="ISO-8859-1", errors='ignore'):
        data += [str(line)]
    return data


# Function: yield_docs()
# Input: files: a list of each file path that we want to index (each file may contain multiple docs)
# Returns: null
# Does: For each file, get the filename and the data (as a list of lists, each sub-list is a line from the file).
# Then separate out each document per file. For each doc, extract the doc number (ID) and the text. Stage that doc
# info to be indexed
def yield_docs(files):
    # iterate over each file (each file may contain multiple documents)
    for count, _file in enumerate(files):
        file_name = _file[_file.rfind("/") + 1:]
        data = get_data_from_text_file(_file)  # everything in one file (may have multiple documents)

        # iterate over each line and add it to docs, which will be each doc as its own list (tokenized)
        docs = []
        current = []
        for element in data:
            doc_end_tag = "</DOC>"
            if doc_end_tag not in element:
                current.append(element)
            else:
                current.append(element)
                docs.append(current)
                current = []

        # docs is a list of lists (one doc for each sub-list)
        # for each doc we now need to get the docno (id), and text
        for doc in docs:
            # join together text
            doc = "".join(doc)
            docend = doc.find("</DOC>")  # index where document end tag starts
            doc_sub = doc[:docend]  # splices off doc end tag
            docno_s = doc_sub.find("<DOCNO>") + len("<DOCNO>")  # index after the doc no start tag
            docno_e = doc_sub.find("</DOCNO>")  # index at start of doc no tag
            docno = doc_sub[docno_s:docno_e].strip()  # this will be the _id
            text_s = doc_sub.find("<TEXT>") + len("<TEXT>")  # index at end of text start tag
            text_e = doc_sub.find("</TEXT")  # start index of text end tag
            text = doc_sub[text_s:text_e].strip() + "\\ln"  # splice out text
            text = text.lower()

            doc_source = {
                "file_name": file_name,
                "text": text
            }
            yield {
                "_index": "ap_dataset",
                "_id": docno,
                "_source": doc_source
            }


# Main code:
# - Set the file path here where docs to be index are stored
# - get file paths for each of those files in "all_files"
file_path = "C:/6200-IR/homework1-mplatt27/IR_data/AP_DATA/ap89_collection/"
all_files = get_files_in_dir(file_path)

# - Bulk add to ES using yield_docs() function
yield_docs(all_files)
try:
    resp = helpers.bulk(es, yield_docs(all_files))
    print("\nhelpers.bulk() RESPONSE:", resp)
    print("RESPONSE TYPE:", type(resp))
except Exception as err:
    print("\nhelpers.bulk() ERROR:", err)
