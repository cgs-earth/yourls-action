# =================================================================
#
# Authors: Benjamin Webb <bwebb@lincolninst.edu>
#
# Copyright (c) 2023 Benjamin Webb
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================


import csv
from datetime import datetime
import mysql.connector
import os
import requests


def connection():
    """Get a connection and a cursor from the pool"""
    db = mysql.connector.connect(pool_name='yourls_loader')
    return (db, db.cursor())


def url_join(*parts):
    """
    helper function to join a URL from a number of parts/fragments.
    Implemented because urllib.parse.urljoin strips subpaths from
    host urls if they are specified
    Per https://github.com/geopython/pygeoapi/issues/695
    :param parts: list of parts to join
    :returns: str of resulting URL
    """
    return '/'.join([p.strip().strip('/') for p in parts])


class yourls:
    # https://stackoverflow.com/questions/60286623/python-loses-connection-to-mysql-database-after-about-a-day
    try:
        mysql.connector.connect(
            host=os.environ.get('YOURLS_DB_HOST') or 'mysql',
            user=os.environ.get('YOURLS_DB_USER') or 'root',
            password=os.environ.get('YOURLS_DB_PASSWORD') or 'arootpassword',
            database="yourls",
            pool_name="yourls_loader",
            pool_size=3
        )
        connection = True
    except mysql.connector.errors.DatabaseError as err:
        print(f'No SQL connection found: {err}')
        connection = False

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.history = set()
        if self.connection:
            mydb, cursor = connection()
            sql_statement = 'DELETE FROM yourls_url WHERE ip = "0.0.0.0"'
            cursor.execute(sql_statement)
            mydb.commit()
            print(cursor.rowcount, "was deleted.")
            cursor.close()
            mydb.close()

    def _check_kwargs(self, keys):
        """
        Parses kwargs for desired keys.

        :param keys: required, list. List of keys to retried from **kwargs.

        :return: generator. key value pairs for each key in **kwargs.

        :raises: pyourls3.exceptions.Pyourls3ParamError
        """
        for key in keys:
            if key in self.kwargs.keys():
                yield key, self.kwargs.get(key)
            else:
                raise ValueError(key)

    def post_mysql(self, filename, csv_=''):
        """
        Sends an API request to shorten a specified CSV.

        :param filename: required, string. Name of CSV to be shortened.
        :param csv_: optional, list. Pre-parsed csv as list of strings.

        :return: dictionary. Full JSON response from the API

        :raises: pyourls3.exceptions.Pyourls3ParamError,
          pyourls3.exceptions.Pyourls3APIError
        """
        print(filename)
        if not filename:
            raise ValueError('filename')

        # Clean input for inserting
        time_ = os.path.getmtime(filename)
        datetime_obj = datetime.fromtimestamp(time_)
        formatted_datetime = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
        extra = [formatted_datetime, '0.0.0.0', 0]

        file = csv_ if csv_ else open(filename, 'r')
        lines = file.split("\n")
        split_ = [line.split(',') for line in lines[:-1]]
        for line in split_:
            if len(line) > 3:
                line[2] = ','.join(line[2:])
                while len(line) > 3:
                    line.pop(-1)
            if len(line) == 3:
                line.extend(extra)

        # Commit file to database
        SQL_STATEMENT = ("INSERT INTO yourls_url "
                         "(`keyword`, `url`, `title`, `timestamp`, `ip`, `clicks`)"  # noqa
                         "VALUES (%s, %s, %s, %s, %s, %s)")
        mydb, cursor = connection()
        try:
            cursor.executemany(SQL_STATEMENT, split_)
        except mysql.connector.errors.ProgrammingError:
            print(split_)

        mydb.commit()
        # print(cursor.rowcount, "was inserted.")
        cursor.close()
        mydb.close()

    def _handle_csvs(self, files):
        """
        Splits list of csv files into individual csv files.

        :param files: required, string. URL to be shortened.
        """
        for f in files:
            self.handle_csv(f)

    def handle_csv(self, file):
        """
        Parses and shortens CSV file.

        :param file: required, name of csv to be shortened
        """
        if isinstance(file, list):
            self._handle_csvs(file)
            return

        parsed_csv = self.parse_csv(file)

        chunky_parsed = self.chunkify(parsed_csv, 10000)
        for chunk in chunky_parsed:
            self.post_mysql(file, chunk)

    def _validate_csvs(self, files):
        """
        Splits list of csv files into individual csv files.

        :param files: required, string. URL to be shortened.
        """
        for f in files:
            self.validate_csv(f)

    def validate_csv(self, file):
        """
        Parses and validates CSV file.

        :param file: required, name of csv to be shortened
        """
        if isinstance(file, list):
            self._validate_csvs(file)
            return

        parsed_csv = self.parse_csv(file)

        chunky_parsed = self.chunkify(parsed_csv, 1)
        uri_stem = self.kwargs['uri_stem']
        for _ in chunky_parsed:
            chunk = _.strip().split(',')
            [pid_, target_] = chunk[:2]
            if pid_ in self.history:
                print(f'Duplicate IRI detected at {uri_stem}{pid_}')
                exit(1)
            else:
                self.history.add(pid_)

    def parse_csv(self, filename):
        """
        Parse CSV file into yourls-friendly csv.

        :param filename: required, string. URL to be shortened.
        :return: list. Parsed csv.
        """
        _ = self._check_kwargs(('keyword', 'long_url', 'title'))
        vals = {k: v for k, v in _}

        try:
            r = requests.get(filename)
            fp = r.content.decode().splitlines()
        except requests.exceptions.MissingSchema:
            r = None
            fp = open(filename, mode='r')

        csv_reader = csv.reader(fp)
        headers = [h.strip() for h in next(csv_reader)]
        ret_csv = []
        for line in csv_reader:
            parsed_line = []
            for k, v in vals.items():
                try:
                    parsed_line.append(line[headers.index(v)].strip())
                except (ValueError, IndexError):
                    continue
            _ = self._check_kwargs(['uri_stem', ])
            ret_csv.append(
                (','.join(parsed_line) + '\n').replace(*[v for k, v in _], ''))

        if not r:
            fp.close()

        return ret_csv

    def chunkify(self, input, n=500):
        """
        Breaks a list of strings into chunks.

        :param input: required, list. List to be chunkified.
        :param n: optional, int. Size of each chunk.
        :return: list. Input list with each sublist length up to the size of n.
        """
        return [''.join(input[i:i + n]) for i in range(0, len(input), n)]
