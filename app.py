import math
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, url_for
from SPARQLWrapper import SPARQLWrapper, JSON
from urllib.parse import urlencode
from jinja2 import Template
from flask_paginate import Pagination, get_page_args, get_page_parameter


# import required module
from PIL import Image
import requests
global_results = []
app = Flask(__name__)

# Define the DBpedia endpoint
sparql = SPARQLWrapper("https://dbpedia.org/sparql")

@app.route('/')
def home():
    '''
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/Monster_Strike.gif/300px-Monster_Strike.gif"

    # Download the image from the URL
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))

    # Get the image width and height
    width, height = img.size

    print(f"Image width: {width}")
    print(f"Image height: {height}")

    '''

    # Define the SPARQL endpoint and query
    endpoint_url = "http://dbpedia.org/sparql"

    # Set the SPARQL query
    query = """
    SELECT DISTINCT ?anime ?title ?episodes ?date ?abstract ?genre
    WHERE {
      ?anime rdf:type dbo:Anime ;
             dbo:abstract ?abstract ;
             dbp:episodes ?episodes;
             dbp:first ?date;
             dbp:genre ?genre;
             foaf:name ?title .
      FILTER (LANG(?abstract) = 'en')
    }
    ORDER BY DESC (?date), DESC(?episodes)
    LIMIT 10
    """
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    urls = []
    anime_results = results["results"]["bindings"]
    for result in anime_results :
        result["title"]["value"] = result["title"]["value"].replace("'", "\\'")
        url = generate_url_by_anime_title(result["title"]["value"])
        urls.append(url)

    return render_template("anime_website.html",results=results["results"]["bindings"], urls = urls)


#de refactorizat
@app.route('/search', methods=['GET','POST'])
def search():

    # Define the SPARQL endpoint and query
    print (request.args.get('query'))
    print (request.args.get('page'))
    print("Date : " + request.form['date'])
    print("End date : " + request.form['endDate'])
    endDate = request.form['endDate']
    date = request.form['date']
    query_keyword = request.form['query']
    query_keyword = query_keyword.replace("'", "\\'")


    # Get the current page from the query parameters, or default to page 1
    page = request.args.get('page',default= 1, type=int)
    return searchPaginated(page,query_keyword, date, endDate)


@app.route('/search/<int:page>/<query>/<date>/<endDate>', methods=['GET'])
@app.route('/search/<int:page>/<query>/<endDate>', methods=['GET'])
@app.route('/search/<int:page>/<query>', methods=['GET'])
def searchPaginated(page, query, date="", endDate=""):

    # Define the SPARQL endpoint and query
    #print(request.args.get('query'))
    print(page)
    print(query)

    # Perform SPARQL query and return results
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    query_statement = generate_query(query, date, endDate)
    sparql.setQuery(query_statement)
    sparql.setReturnFormat(JSON)
    all_results = sparql.query().convert()['results']['bindings']

    # Calculate the number of results to display per page
    results_per_page = 10

    # Calculate the start and end indices of the results to display on the current page
    start_index = (page - 1) * results_per_page
    end_index = start_index + results_per_page

    # Slice the results to only include the current page
    total_results = len(all_results)
    results = all_results[start_index:end_index]

    # Calculate the total number of pages for the search results
    num_pages = math.ceil(len(all_results) / results_per_page)

    # Determine if there is a previous page and/or a next page
    has_prev = page > 1
    has_next = page < num_pages

    # Generate pagination object
    #pagination = Pagination(page=page, total=total_results, per_page=results_per_page)
    print("Value of page before render: " + str(page))

    # Render the search results template with the current page, total number of pages, and results
    return render_template('search_results.html', results=results, current_page=page, num_pages=num_pages, has_prev=has_prev, has_next=has_next,
                           query=query, page=page, date=date, endDate=endDate)#, pagination=pagination)




@app.route('/destination/<int:page>/<query>/<int:loop_index>/<date>/<endDate>',methods=['GET'])
@app.route('/destination/<int:page>/<query>/<int:loop_index>/<endDate>',methods=['GET'])
@app.route('/destination/<int:page>/<query>/<int:loop_index>',methods=['GET'])
def destination(page,query, loop_index, date="", endDate=""):

    print(page)
    print(query)

    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    query_statement = generate_query(query, date, endDate)
    sparql.setQuery(query_statement)
    sparql.setReturnFormat(JSON)
    all_results = sparql.query().convert()['results']['bindings']

    # Calculate the number of results to display per page
    results_per_page = 10

    # Calculate the start and end indices of the results to display on the current page
    start_index = (page - 1) * results_per_page
    end_index = start_index + results_per_page

    # Slice the results to only include the current page
    total_results = len(all_results)
    results = all_results[start_index:end_index]

    result = results[loop_index]
    # Calculate the total number of pages for the search results
    num_pages = math.ceil(len(all_results) / results_per_page)

    # Determine if there is a previous page and/or a next page
    has_prev = page > 1
    has_next = page < num_pages

    # Generate pagination object
    # pagination = Pagination(page=page, total=total_results, per_page=results_per_page)
    print("Value of page before render: " + str(page))


    url = generate_url_by_anime_title(result["title"]["value"])




    return render_template('destination.html', result=result, url = url)



@app.context_processor
def utility_processor():
    def generate_search_url(query,page):
        return url_for('searchPaginated', query=query, page=page)
    return dict(generate_search_url=generate_search_url)




def generate_query(query_keyword, startDate, endDate):

    if startDate == "":
        query = """
                SELECT DISTINCT ?anime ?title ?episodes ?date ?abstract (CONCAT(UCASE(SUBSTR(REPLACE(LCASE(SUBSTR(STR(?genre), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 1, 1)), SUBSTR(REPLACE(LCASE(SUBSTR(STR(?genre), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 2)) AS ?genre_name)
             WHERE {
                     ?anime rdf:type dbo:Anime ;
                      dbo:abstract ?abstract ;
                      dbp:episodes ?episodes;
                      dbp:first ?date;
                      dbp:genre ?genre;
                      foaf:name ?title .
                     FILTER CONTAINS(?title, \'""" + query_keyword + """\')
                     FILTER (?date <= \'""" + endDate + """\'^^xsd:date)
                    }
                """
    else:
        query = """
                      SELECT DISTINCT ?anime ?title ?episodes ?date ?abstract (CONCAT(UCASE(SUBSTR(REPLACE(LCASE(SUBSTR(STR(?genre), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 1, 1)), SUBSTR(REPLACE(LCASE(SUBSTR(STR(?genre), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 2)) AS ?genre_name)
                   WHERE {
                           ?anime rdf:type dbo:Anime ;
                            dbo:abstract ?abstract ;
                            dbp:episodes ?episodes;
                            dbp:first ?date;
                            dbp:genre ?genre;
                            foaf:name ?title .
                           FILTER CONTAINS(?title, \'""" + query_keyword + """\')
                           FILTER (?date >= \'""" + startDate + """\'^^xsd:date && ?date <= \'""" + endDate + """\'^^xsd:date)
                          }
                      """
    return query


def generate_url_by_anime_title(anime_title):
    search_term = "Casshan: Robot Hunter"
    url = f"https://www.google.com/search?q={anime_title}&tbm=isch"

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    image = soup.find("img", class_="yWs4tf")
    print(image["src"])
    return image["src"]

if __name__ == '__main__':
    app.run()