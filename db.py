#!/usr/bin/env python3
"""

    Ensk.is - Free and open English-Icelandic dictionary

    Copyright (c) 2022, Sveinbjorn Thordarson <sveinbjorn@sveinbjorn.org>
    All rights reserved.

    Redistribution and use in source and binary forms, with or without modification,
    are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice, this
    list of conditions and the following disclaimer in the documentation and/or other
    materials provided with the distribution.

    3. Neither the name of the copyright holder nor the names of its contributors may
    be used to endorse or promote products derived from this software without specific
    prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
    IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
    INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
    NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
    PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
    WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.


    Dictionary database singleton.


"""


from typing import List, Dict

import logging
import sqlite3
from pathlib import Path


DB_FILENAME = "dict.db"


class EnskDatabase(object):
    _instance = None
    _dbname = DB_FILENAME

    def __init__(self):
        self.db_conn = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            logging.info("Instantiating database")
            cls._instance = super(EnskDatabase, cls).__new__(cls)
            # Create database file and schema if no DB file exists
            if not Path(cls._dbname).is_file():
                cls._instance.create()
        return cls._instance

    def create(self) -> None:
        """Create database file and generate database schema."""
        logging.info(f"Creating database {self._dbname}")

        # Create database file
        conn = sqlite3.connect(self._dbname)

        # Create table
        create_table_sql = """
            CREATE TABLE dictionary (
                id INTEGER UNIQUE PRIMARY KEY NOT NULL,
                word TEXT,
                definition TEXT,
                ipa_uk TEXT,
                ipa_us TEXT,
                page_num INTEGER
            );
        """

        conn.cursor().execute(create_table_sql)

    def conn(self, read_only: bool = False) -> sqlite3.Connection:
        """Open database connection lazily."""
        if not self.db_conn:
            # Open database file via URI
            db_uri = f"file:{self._dbname}"
            if read_only:
                db_uri += "?mode=ro"
            logging.info(f"Opening database connection at {db_uri}")
            self.db_conn = sqlite3.connect(
                db_uri, uri=True, check_same_thread=(read_only == False)
            )

            # Return rows as key-value dicts
            self.db_conn.row_factory = lambda c, r: dict(
                zip([col[0] for col in c.description], r)
            )

        return self.db_conn

    def add_entry(
        self,
        w: str,
        definition: str,
        ipa_uk: str,
        ipa_us: str,
        page_num: int,
        commit=False,  # Whether to commit changes to database immediately
    ) -> None:
        """Add a single entry to the dictionary."""
        conn = self.conn()
        conn.cursor().execute(
            "INSERT INTO dictionary (word, definition, ipa_uk, ipa_us, page_num) VALUES (?,?,?,?,?)",
            [w, definition, ipa_uk, ipa_us, page_num],
        )
        if commit:
            conn.commit()

    def read_all_entries(self) -> List[Dict]:
        """Read and return all entries."""
        conn = self.conn()
        selected = conn.cursor().execute("SELECT * FROM dictionary")
        res = list(selected)  # Consume generator into list
        res.sort(key=lambda x: x["word"].lower())
        return res

    def read_all_additions(self) -> List[Dict]:
        """Read and return all entries not present in the original Zoega dictionary."""
        conn = self.conn()
        selected = conn.cursor().execute("SELECT * FROM dictionary WHERE page_num=0")
        res = list(selected)  # Consume generator into list
        res.sort(key=lambda x: x["word"].lower())
        return res

    def read_all_duplicates(self) -> List[Dict]:
        """Read and return all duplicate (i.e. same word) entries present in the dictionary
        as a dict keyed by word."""
        conn = self.conn()
        # TODO: Make this work, return as dict keyed by word
        selected = conn.cursor().execute(
            "SELECT *, COUNT(*) FROM dictionary HAVING COUNT(*) > 1"  # FIXME
        )
        res = list(selected)  # Consume generator into list
        return res
