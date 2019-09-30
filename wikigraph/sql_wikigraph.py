
import sys, os, time
from collections import MutableMapping
import sqlite3
import pickle

# _inc_temp = '''UPDATE articles SET num = num + 1 WHERE name IN ({})'''
# _insert_temp = '''INSERT INTO articles VALUES (?,1);'''
# _sel_id_temp = '''SELECT rowid FROM articles WHERE name IN ({})'''
# _sel_name_temp = '''SELECT name FROM articles WHERE rowid IN ({})'''
# _sel_full_id_temp = '''SELECT * FROM articles WHERE rowid IN ({})'''
# _sel_full_name_temp = '''SELECT * FROM articles WHERE name IN ({})'''



#_sel_temp = '''SELECT {} FROM {} WHERE {}'''

# _sel_out_links = '''SELECT toID FROM links WHERE fromID IN ({});'''
# _sel_in_links = '''SELECT fromID FROM links WHERE toID IN ({});'''
#
# _sel_single_out_links = '''SELECT toID FROM links WHERE fromID = ?;'''
# _sel_single_in_links = '''SELECT fromID FROM links WHERE toID = ?;'''
#
# _set_expanded = '''UPDATE articles SET status = 1 WHERE name = ?;'''
#
# _insert_article = '''INSERT INTO articles VALUES (?,0);'''
# _insert_link = '''INSERT INTO links VALUES (?,?);'''
# _insert_redir_name = '''INSERT INTO redirects_names VALUES (?);'''
# _insert_redir = '''INSERT INTO redirects VALUES (?,?);'''
#
# _sel_name_temp = '''SELECT name FROM articles WHERE rowid IN ({})'''
# _sel_id_temp = '''SELECT rowid FROM articles WHERE name IN ({})'''


_sel_ID = '''SELECT rowid FROM articles WHERE name = ?'''
_insert_ID = '''INSERT INTO articles VALUES (?,0);'''
_sel_rID = '''SELECT rowid FROM redirects_names WHERE name = ?'''
_insert_rID = '''INSERT INTO redirects_names VALUES (?);'''
_insert_edges_temp = '''INSERT INTO {} VALUES (?,?);'''
_update_status = '''UPDATE articles SET status = 1 WHERE rowid = ?;'''


def create_database(path):
	if os.path.isfile(path):
		raise Exception('File {} already exists, overwriting is not permitted'.format(path))

	path_dir = os.path.dirname(path)
	if len(path_dir) and not os.path.isdir(path_dir):
		os.makedirs(path_dir)
		print('Created dir: {}'.format(path_dir))

	conn = sqlite3.connect(path)

	c = conn.cursor()

	c.execute('''CREATE TABLE articles (
	name TEXT PRIMARY KEY,
	status INT)''')

	c.execute('''CREATE TABLE links (
	fromID INT,
	toID INT,
	PRIMARY KEY (fromID, toID),
	FOREIGN KEY(fromID) REFERENCES articles(rowid),
	FOREIGN KEY(toID) REFERENCES articles(rowid)) WITHOUT ROWID;''')

	c.execute('''CREATE TABLE redirects_names (
		name TEXT PRIMARY KEY)''')

	c.execute('''CREATE TABLE redirects (
		aID INT,
		rID INT,
		PRIMARY KEY (aID, rID),
		FOREIGN KEY(aID) REFERENCES articles(rowid),
		FOREIGN KEY(rID) REFERENCES redirects_names(rowid)) WITHOUT ROWID;''')

	conn.commit()
	conn.close()

class WikiGraph_DB(object):
	def __init__(self, db_path):
		self.conn = sqlite3.connect(db_path)
		self.cursor = self.conn.cursor()

		self.update_working_sets()


	def update_working_sets(self):

		self.expanded = set()
		self.inserted = set()
		self.inserted_redirs = set()

		print('Updating working sets ({} entries) ...'.format(self.article_count()), end='')
		sys.stdout.flush()

		self.cursor.execute('''SELECT name, status FROM articles''')

		for name, expanded in self.cursor:

			if expanded == 1:
				self.expanded.add(name)
			self.inserted.add(name)

		self.cursor.execute('''SELECT name FROM redirects_names''')
		self.inserted_redirs.update([el[0] for el in self.cursor])


		db_count = self.article_count()
		assert db_count == len(self.inserted), '{} vs {}'.format(db_count, len(self.inserted))

		print('done: expanded={}, inserted={}, redirs={}'.format(
			len(self.expanded), len(self.inserted), len(self.inserted_redirs)))

	def names(self):
		self.cursor.execute('''SELECT name FROM articles''')
		return iter(self.cursor)

	def items(self):
		self.cursor.execute('''SELECT * FROM articles''')
		return iter(self.cursor)

	# def add_articles(self, *names):
	# 	for name in names:
	# 		try:
	# 			self.cursor.execute(_insert_temp, (name,))
	# 		except sqlite3.IntegrityError:
	# 			pass
	# 	# self.cursor.executemany(_insert_temp, [(n,) for n in names])
	# 	self.conn.commit()

	def create_IDs(self, names):


		results = []

		for name in names:

			if name in self.inserted:

				ID = self.cursor.execute(_sel_ID, (name,)).fetchall()[0][0]

			else:

				self.cursor.execute(_insert_ID, (name,))
				self.inserted.add(name)

				ID = len(self.inserted)

			results.append(ID)

		return results

	def create_rIDs(self, names):

		results = []

		for name in names:

			if name in self.inserted_redirs:

				ID = self.cursor.execute(_sel_rID, (name,)).fetchall()[0][0]

			else:

				try:

					self.cursor.execute(_insert_rID, (name,))
					self.inserted_redirs.add(name)

				except:
					print(name in self.inserted_redirs, name)
					print(self.cursor.execute(_sel_rID, (name,)).fetchall()[0][0])
					print(len(self.inserted_redirs), self.redir_count())
					quit()

				ID = len(self.inserted_redirs)

			results.append(ID)

		return results

	def add_edges(self, fromID, toIDs, table='links'):

		cmd = _insert_edges_temp.format(table)

		self.cursor.executemany(cmd, [(fromID, toID) for toID in toIDs])


	def add(self, name, links, redirs):

		if name in self.expanded:
			print('**Error: Already expanded {}'.format(name))
			return

		ID = self.create_IDs([name])[0]

		self.cursor.execute(_update_status, (ID,))
		self.expanded.add(name)

		links = self.create_IDs(links)
		redirs = self.create_rIDs(redirs)

		self.add_edges(ID, links, table='links')
		self.add_edges(ID, redirs, table='redirects')

		self.conn.commit()

	def __len__(self):
		return len(self.expanded)

	def article_count(self):
		self.cursor.execute('''SELECT COUNT(*) FROM articles''')
		return self.cursor.fetchall()[0][0]

	def redir_count(self):
		self.cursor.execute('''SELECT COUNT(*) FROM redirects_names''')
		return self.cursor.fetchall()[0][0]

	# def get_id(self, *names):
	# 	self.cursor.execute(_sel_id_temp.format(', '.join('?' * len(names))), names)
	# 	return self.cursor.fetchall()
	#
	# def get_name(self, *IDs):
	# 	self.cursor.execute(_sel_name_temp.format(', '.join('?' * len(IDs))), IDs)
	# 	return self.cursor.fetchall()
	#
	# def get_full_from_names(self, *names):
	# 	self.cursor.execute(_sel_full_name_temp.format(', '.join('?' * len(names))), names)
	# 	return self.cursor.fetchall()
	#
	# def get_full_from_ids(self, *IDs):
	# 	self.cursor.execute(_sel_full_id_temp.format(', '.join('?' * len(IDs))), IDs)
	# 	return self.cursor.fetchall()

	def __del__(self):
		self.conn.close()

















class PersistentDict(MutableMapping):
	def __init__(self, dbpath, iterable=None, **kwargs):
		self.dbpath = dbpath
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'create table if not exists memo '
				'(key blob primary key not null, value blob not null)'
			)
		if iterable is not None:
			self.update(iterable)
		self.update(kwargs)

	def encode(self, obj):
		return pickle.dumps(obj)

	def decode(self, blob):
		return pickle.loads(blob)

	def get_connection(self):
		return sqlite3.connect(self.dbpath)

	def  __getitem__(self, key):
		key = self.encode(key)
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'select value from memo where key=?',
				(key,)
			)
			value = cursor.fetchone()
		if value is None:
			raise KeyError(key)
		return self.decode(value[0])

	def __setitem__(self, key, value):
		key = self.encode(key)
		value = self.encode(value)
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'insert or replace into memo values (?, ?)',
				(key, value)
			)

	def __delitem__(self, key):
		key = self.encode(key)
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'select count(*) from memo where key=?',
				(key,)
			)
			if cursor.fetchone()[0] == 0:
				raise KeyError(key)
			cursor.execute(
				'delete from memo where key=?',
				(key,)
			)

	def __iter__(self):
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'select key from memo'
			)
			records = cursor.fetchall()
		for r in records:
			yield self.decode(r[0])

	def __len__(self):
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'select count(*) from memo'
			)
			return cursor.fetchone()[0]


class PersistentDict_Simple(MutableMapping):
	def __init__(self, dbpath, iterable=None, **kwargs):
		self.dbpath = dbpath
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'create table if not exists memo '
				'(key blob primary key not null, value blob not null)'
			)
		if iterable is not None:
			self.update(iterable)
		self.update(kwargs)

	def encode(self, obj):
		return pickle.dumps(obj)

	def decode(self, blob):
		return pickle.loads(blob)

	def get_connection(self):
		return sqlite3.connect(self.dbpath)

	def  __getitem__(self, key):
		key = self.encode(key)
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'select value from memo where key=?',
				(key,)
			)
			value = cursor.fetchone()
		if value is None:
			raise KeyError(key)
		return self.decode(value[0])

	def __setitem__(self, key, value):
		key = self.encode(key)
		value = self.encode(value)
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'insert or replace into memo values (?, ?)',
				(key, value)
			)

	def __delitem__(self, key):
		key = self.encode(key)
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'select count(*) from memo where key=?',
				(key,)
			)
			if cursor.fetchone()[0] == 0:
				raise KeyError(key)
			cursor.execute(
				'delete from memo where key=?',
				(key,)
			)

	def __iter__(self):
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'select key from memo'
			)
			records = cursor.fetchall()
		for r in records:
			yield self.decode(r[0])

	def __len__(self):
		with self.get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				'select count(*) from memo'
			)
			return cursor.fetchone()[0]


