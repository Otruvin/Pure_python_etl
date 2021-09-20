import argparse
import re
from argparse import Namespace
from csv import reader
import logging
import time
from datetime import date
from typing import Sequence, Optional, Final, Callable


pathRatings: Final = 'files/ratings_ml_small.csv'
pathMovies: Final = 'files/movies_ml_small.csv'


def parseArgs(argv: Optional[Sequence[str]]) -> Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-N',
                        type=int,
                        help="Count of films to selected")
    parser.add_argument('-reg', '--regex',
                        type=str,
                        help="Regular expression for search films by name")
    parser.add_argument('-yf', '--year_from',
                        type=int,
                        help="Oldest year release of selected films")
    parser.add_argument('-yt', '--year_to',
                        type=int,
                        help='Latest year release of selected films')
    parser.add_argument('-g', '--genres',
                        type=str,
                        help='Genres of films to search')
    parser.add_argument('-tp', '--time_print',
                        action='store_true',
                        help='Print time of work program')
    parser.add_argument('-l', '--err_log',
                        action='store_true',
                        help='log the errors')

    args = parser.parse_args(argv)
    return args


def checkGenres(searchGenres: Optional[list], columnGenres: Optional[list]) -> bool:
    """
    check contains seraching genre in movie genres

    Parameters
    __________
    searchGenres: dict   search genres
    columnGenres: list   genres of movie

    Returns
    _______
    bool
    """
    if columnGenres == '(no genres listed)':
        return False

    if searchGenres is None:
        if columnGenres is None:
            return False
        return True

    if searchGenres and columnGenres:
        for genre in searchGenres:
            if genre in columnGenres:
                return True
    return False


def checkWithSearchParametersFilms(argumentsSearch: list, columns: list) -> bool:
    """
    Checking if the given search parameters for movies are met

    Parameters
    __________
    argumentsSearch: dict   search parameters
    columns:         list   columns from line

    Returns
    _______
    bool
    """
    regularExpr, yearFrom, yearTo, genreSearch = argumentsSearch
    year, title, genres = columns

    if year:
        if yearFrom and yearFrom > year:
            return False
        if yearTo and yearTo < year:
            return False
    else:
        return False
    if title:
        if regularExpr:
            if not bool(re.search(regularExpr, title)):
                return False
    else:
        return False

    return checkGenres(genreSearch, genres)


def parseLineMovies(line: list) -> tuple:
    """
    Parse line from movies

    Parameters
    __________
    line: list   line to parse

    Returns
    _______
    tuple
    """
    id, title, genre = line
    year = None
    matchYear = re.search(r"(?<=\()(\d{4})(?=\))", title)
    if matchYear:
        year = int(matchYear.group())
    if year is None:
        name = title
    else:
        matchName = re.search(r".+?(?= \(\d{4})", title)
        if matchName:
            name = matchName.group()
        else:
            name = None
    if re.search('[()]', genre):
        genresList = None
    else:
        genresList = genre.split("|")

    return int(id), year, name, genresList


def readFileMovies(pathFile: str, conditions: list, parseLine: Callable[[list], tuple]) -> dict:
    """
    Read file movies

    Parameters
    __________
    pathFile: str                        path to file to read
    conditions: list                     search parameters
    parseLine: Callable[[list], tuple]   function to parse lines

    Returns
    _______
    dict
    """
    try:
        res = {}
        with open(pathFile) as f:
            next(f)
            csv_reader = reader(f)
            for line in csv_reader:
                lineParsed = parseLine(line)
                if checkWithSearchParametersFilms(conditions, lineParsed[1:4]):
                    res[lineParsed[0]] = lineParsed[1:4]
    except EnvironmentError as e:
        raise EnvironmentError("Env error. Error: {0}".format(e))

    return res


def getRatings(pathFile: str, movies: dict) -> dict:
    """
    Get average ratings from ratings file

    Parameters
    __________
    pathFile: str    path to file to read
    movies:   dict   id of selected films

    Returns
    _______
    dict
    """
    try:
        res = {}
        with open(pathFile) as f:
            next(f)
            csv_reader = reader(f)
            for _, idMovie, rating, _ in csv_reader:
                idMovie = int(idMovie)
                if idMovie in movies:
                    if idMovie not in res:
                        res[idMovie] = [0, 0]
                    res[idMovie][0] += float(rating)
                    res[idMovie][1] += 1
        for key, value in res.items():
            res[key] = value[0] / value[1]
    except (EnvironmentError, ZeroDivisionError) as e:
        raise ValueError("Env error. Error: {0}".format(e))

    return res


def joinResults(movies: dict, ratings: dict) -> dict:
    """
    Join movies to ratings

    Parameters
    __________
    movies:  dict   filtered data with movies
    ratings: dict   ratings for selected movies

    Returns
    _______
    dict
    """
    for key in ratings.keys():
        ratings[key] = ratings[key], *movies[key]
    ratings = {k: v for k, v in sorted(ratings.items(), key = lambda item: (-item[1][0], -item[1][1], item[1][2]))}
    return ratings


def printAllResults(results: dict, genres: set, showEmpty: bool, border: int = None) -> None:
    """
    Print all results

    Parameters
    __________
    results:   str      all data to print
    genres:    dict     genres to print
    showEmpty: bool     show films with empty genres
    border:    border   border count of printing films

    Returns
    _______
    None
    """
    print("genre,title,year,rating")
    genres = sorted(genres)
    for genre in genres:
        count = 0
        for k, v in results.items():
            if v[3] and genre in v[3]:
                if v[1]:
                    print('{0},"{1}",{2},{3}'.format(genre, v[2], v[1], round(v[0], 1)))
                else:
                    print('{0},"{1}",,{3}'.format(genre, v[2], v[1], round(v[0], 1)))
                count += 1
                if border == count:
                    break
    if showEmpty:
        count = 0
        for k, v in results.items():
            if not v[3]:
                print(',"{0}",{1},{2}'.format(v[2], v[1], round(v[0], 1)))
                count += 1
            if border == count:
                break


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parseArgs(argv)

    tic = time.perf_counter()

    if args.err_log:
        logging.basicConfig(filename='logs.log', level=logging.ERROR)

    if args.genres:
        genres = args.genres.split("|")
    else:
        genres = None

    conditions = [args.regex, args.year_from, args.year_to, genres]

    try:
        movies = readFileMovies(pathMovies, conditions, parseLineMovies)
        ratings = getRatings(pathRatings, movies)
    except Exception as e:
        if args.err_log:
            logging.error('Date: {0}. Error while reading files. Error: {1}'.format(date.today().strftime("%d/%m/%Y"), e))
        return 1

    results = joinResults(movies, ratings)
    allGenres = set()
    empty = False

    if not genres:
        allGenres = set()
        for k, v in results.items():
            if v[3]:
                allGenres.update(v[3])
        empty = True
    else:
        allGenres.update(genres)

    printAllResults(results, allGenres, empty, args.N)

    toc = time.perf_counter()

    if args.time_print:
        print(f"\nTime of work {toc - tic:0.4f} seconds")

    return 0


if __name__ == '__main__':
    exit(main())
