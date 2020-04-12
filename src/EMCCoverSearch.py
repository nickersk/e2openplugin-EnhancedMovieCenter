﻿# -*- coding: utf-8 -*-
# mod by einfall (09.11.2014)
# change to themoviedb.org / thetvdb.com - Api

from __init__ import _

from Components.ActionMap import *
from Components.Label import Label
from Components.MenuList import MenuList

from Components.MultiContent import MultiContentEntryText
from Components.Pixmap import Pixmap
from enigma import ePicLoad, gPixmapPtr
from Tools.LoadPixmap import LoadPixmap
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Tools.Directories import fileExists
from Screens.Menu import boundFunction
from Screens.LocationBox import LocationBox
from Components.PluginComponent import plugins

from Components.Button import Button

from twisted.web import client
from twisted.web.client import downloadPage, getPage
from twisted.internet import defer

from Components.config import *
from configlistext import ConfigListScreenExt

from enigma import eListboxPythonMultiContent, eListbox, gFont, getDesktop, loadJPG, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, loadPNG, RT_WRAP, eServiceReference

from Tools.BoundFunction import boundFunction
from DelayedFunction import DelayedFunction
from time import time

from MovieCenter import getMovieNameWithoutExt, getMovieNameWithoutPhrases, getNoPosterPath

sz_w = getDesktop(0).size().width()

import re, urllib, urllib2, os, time, shutil, requests

config.EMC.imdb = ConfigSubsection()
#search/automatic
config.EMC.imdb.search = ConfigSelection(default='1', choices=[('1', _("themoviedb.org for movies + thetvdb.com for series (e.g. 'S01E01' in title)"))])
config.EMC.imdb.search_filter = ConfigSelection(default='3', choices=[('0', _('overall')), ('2', _('two contiguous')), ('3', _('three contiguous'))])
config.EMC.imdb.savetotxtfile = ConfigYesNo(default = False)
#single/manually
config.EMC.imdb.singlesearch = ConfigSelection(default='6', choices=[('0', _('imdb.com')), ('1', _('thetvdb.com')), ('2', _('csfd.cz')), ('3', _('all')), ('4', _('themoviedb.org')), ('5', _('themoviedb.org + thetvdb.com')), ('6', _('themoviedb.org + thetvdb.com + imdb.com'))])
config.EMC.imdb.singlesearch_filter = ConfigSelection(default='2', choices=[('0', _('overall')), ('1', _('every single one')), ('2', _('two contiguous')), ('3', _('three contiguous'))])
config.EMC.imdb.singlesearch_siteresults = ConfigSelection(default='3', choices=[('0', _('no limit')),'3', '5', '10', '25', '50', '100'])
config.EMC.imdb.singlesearch_tvdbcoverrange = ConfigSelection(default='1', choices = [('0', _('no limit')), ('1', _('standard cover')), '3', '5', '10', '25'])
config.EMC.imdb.singlesearch_foldercoverpath = ConfigSelection(default='0', choices=[('0', _('.../foldername/foldername.jpg')), ('1', _('.../foldername.jpg')), ('2', _('.../foldername/folder.jpg'))])
#common
config.EMC.imdb.preferred_coversize = ConfigSelection(default="w185", choices = ["w92", "w154", "w185", "w300", "w320", "w342", "w500", "w780", "original"])
config.EMC.imdb.thetvdb_standardcover = ConfigSelectionNumber(default = 1, stepwidth = 1, min = 1, max = 30, wraparound = True)


def urlExist(url):
	try:
		urllib2.urlopen(urllib2.Request(url))
		return True
	except:
		return False

def getSearchList(title, option):
	slist = []
	s = title.replace('.',' ').replace('_',' ').replace('-',' ').replace('+', ' ').split()
	if option == '1':
		slist = s
	elif option == '2':
		for x in range(len(s)-1):
			slist.append(s[x] + ' ' + s[x+1])
	elif option == '3':
		for x in range(len(s)-2):
			slist.append(s[x] + ' ' + s[x+1] + ' ' + s[x+2])
	if not slist:
		slist = [' '.join(s)]
	return slist

try:
	from enigma import eMediaDatabase
	isDreamOS = True
except:
	isDreamOS = False

class imdblist(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 14))
		self.l.setFont(1, gFont("Regular", 16))
		self.l.setFont(2, gFont("Regular", 18))
		self.l.setFont(3, gFont("Regular", 20))
		self.l.setFont(4, gFont("Regular", 22))
		self.l.setFont(5, gFont("Regular", 24))
		self.l.setFont(6, gFont("Regular", 28))
		self.l.setFont(7, gFont("Regular", 54))

class EMCImdbScan(Screen):
	if sz_w == 1920:
		skin = """
			<screen position="center,110" size="1800,930" title="EMC Cover search">
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/red.png" position="10,5" size="300,70" alphatest="blend"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/green.png" position="310,5" size="300,70" alphatest="blend"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/yellow.png" position="610,5" size="300,70" alphatest="blend"/>
				<widget backgroundColor="#9f1313" font="Regular;30" halign="center" name="ButtonRedText" position="10,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
				<widget backgroundColor="#1f771f" font="Regular;30" halign="center" name="ButtonGreenText" position="310,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
				<widget backgroundColor="#a08500" font="Regular;30" halign="center" name="Manage Cover" position="610,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
				<widget font="Regular;34" halign="right" position="1650,25" render="Label" size="120,40" source="global.CurrentTime">
				    <convert type="ClockToText">Default</convert>
				</widget>
				<widget font="Regular;34" halign="right" position="1240,25" render="Label" size="400,40" source="global.CurrentTime" >
				    <convert type="ClockToText">Date</convert>
				</widget>
				<eLabel backgroundColor="#818181" position="10,80" size="1780,1" />
				<widget name="info" position="10,90" size="400,32" halign="center" font="Regular;28"/>
				<widget name="poster" position="10,130" size="400,600" alphatest="blend"/>
				<widget name="m_info" position="440,90" size="1350,40" font="Regular;34" halign="center" valign="center" foregroundColor="yellow"/>
				<widget name="menulist" position="440,140" size="1350,675" itemHeight="45" scrollbarMode="showOnDemand" enableWrapAround="1"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/menu.png" position="10,880" size="80,40" alphatest="blend"/>
				<widget name="Setup" position="110,882" size="380,40" font="Regular;30" valign="center" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/ok.png" position="510,880" size="80,40" alphatest="blend"/>
				<widget name="Single search" position="610,882" size="280,40" font="Regular;30" valign="center" />
				<widget name="exist" position="10,740" size="400,35" font="Regular;30"/>
				<widget name="no_poster" position="10,780" size="400,35" font="Regular;30"/>
				<widget name="download" position="10,820" size="400,35" font="Regular;30"/>
				<widget name="done_msg" position="930,850" size="860,70" font="Regular;30" halign="right" foregroundColor="yellow" valign="bottom"/>
			</screen>"""
	else:
		skin = """
	    		<screen position="center,80" size="1200,610" title="EMC Cover search">
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/red.png" position="10,5" size="200,40" alphatest="blend"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/green.png" position="210,5" size="200,40" alphatest="blend"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/yellow.png" position="410,5" size="200,40" alphatest="blend"/>
				<widget name="ButtonRedText" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
				<widget name="ButtonGreenText" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
				<widget name="Manage Cover" position="410,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
				<widget source="global.CurrentTime" render="Label" position="1130,12" size="60,25" font="Regular;22" halign="right">
					<convert type="ClockToText">Default</convert>
				</widget>
				<widget source="global.CurrentTime" render="Label" position="820,12" size="300,25" font="Regular;22" halign="right">
					<convert type="ClockToText">Format:%A %d. %B</convert>
				</widget>
				<eLabel position="10,50" size="1180,1" backgroundColor="#818181" />
				<widget name="info" position="20,55" size="220,55" halign="center" valign="center" font="Regular;22"/>
				<widget name="poster" position="20,120" size="220,330" alphatest="blend"/>
				<widget name="m_info" position="270,55" size="920,55" font="Regular;24" halign="center" valign="center" foregroundColor="yellow"/>
				<widget name="menulist" position="270,120" size="920,420" itemHeight="30" scrollbarMode="showOnDemand" enableWrapAround="1"/>
				<widget name="exist" position="10,470" size="220,25" font="Regular;20"/>
				<widget name="no_poster" position="10,500" size="220,25" font="Regular;20"/>
				<widget name="download" position="10,530" size="220,25" font="Regular;20"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/menu.png" position="20,570" size="60,30" alphatest="blend"/>
				<widget name="Setup" position="100,571" size="200,30" font="Regular;22" valign="center" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/ok.png" position="320,570" size="60,30" alphatest="blend"/>
				<widget name="Single search" position="400,571" size="190,30" font="Regular;22" valign="center" />
				<widget name="done_msg" position="590,548" size="600,50" font="Regular;20" halign="right" foregroundColor="yellow" valign="bottom"/>
			</screen>"""

	def __init__(self, session, data, folder=False):
		Screen.__init__(self, session, data)
		self.m_list = data
		self.isFolder = folder
		self["actions"] = HelpableActionMap(self, "EMCimdb",
		{
			"EMCEXIT":	self.exit,
			"EMCOK":	self.ok,
			"EMCGreen":	self.imdb,
			"EMCRed":	self.red,
			"EMCYellow":	self.verwaltung,
			"EMCRedLong":	self.redLong,
			"EMCMenu":	self.config,
		}, -1)

		self["ButtonGreen"] = Pixmap()
		self["ButtonGreenText"] = Label(_("Search"))
		self["ButtonRed"] = Pixmap()
		self["ButtonRedText"] = Label(_("Delete"))
		self["poster"] = Pixmap()
		self.menulist = []
		self["menulist"] = imdblist([])
		self["info"] = Label("")
		self["m_info"] = Label("")
		self["genre"] = Label("")
		self["download"] = Label("")
		self["exist"] = Label("")
		self["no_poster"] = Label("")
		self["done_msg"] = Label(_("Press green button to start search"))
		self["info"].setText("")
		self["Manage Cover"] = Label(_("Manage Cover"))
		self["Setup"] = Label(_("Setup"))
		self["Single search"] = Label(_("Single search"))
		self.no_image_poster = getNoPosterPath() #"/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png"
		self.check = False
		self["menulist"].onSelectionChanged.append(self.showInfo)
		self.running = False

		self.picload = ePicLoad()
		#self.picload_conn = self.picload.PictureData.connect(self.showCoverCallback)
		self.file_format = "(\.3g2|\.3gp|\.asf|\.avi|\.dat|\.divx|\.f4v|\.flv|\.img|\.iso|\.m2ts|\.m4v|\.mkv|\.mov|\.mp4|\.mpe|\.mpeg|\.mpg|\.mts|\.ogm|\.ogv|\.pva|\.rm|\.rmvb|\.stream|\.ts|\.vob|\.webm|\.wmv|\.wtv)"
		self.onLayoutFinish.append(self.layoutFinished)

		self.showSearchSiteName = "TMDb+TVDb"

	def layoutFinished(self):
		self.listWidth = self["menulist"].instance.size().width()
		self.listHeight = self["menulist"].instance.size().height()
		self.itemHeight = self["menulist"].l.getItemSize().height()
		self.setTitle(_("EMC Cover search"))
		if self.isFolder:
			del self["actions"].actions['EMCGreen']
			del self["actions"].actions['EMCYellow']
			self["ButtonGreenText"].setText(" ")
			self["Manage Cover"].setText(" ")
			self["done_msg"].setText(" ")
			self.verwaltung()

	def verwaltung(self):
		self.menulist = []
		self.count_movies = len(self.m_list)
		self.vm_list = self.m_list[:]
		count_existing = 0
		count_na = 0

		#for each in sorted(self.vm_list):
		for each in self.vm_list:
			(title, path) = each
			if self.isFolder:
				if config.EMC.imdb.singlesearch_foldercoverpath.value == '1':
					path = path + '.jpg'
				elif config.EMC.imdb.singlesearch_foldercoverpath.value == '2':
					path = path + os.sep + 'folder.jpg'
				else:
					path = path + os.sep + title + '.jpg'
			#title = getMovieNameWithoutPhrases(getMovieNameWithoutExt(title))
			path = re.sub(self.file_format + "$", '.jpg', path, flags=re.IGNORECASE)
			if os.path.exists(path):
				count_existing += 1
				self.menulist.append(self.imdb_show(title, path, _("Exist"), "", title))
			else:
				count_na += 1
				self.menulist.append(self.imdb_show(title, path, _("N/A"), "", title))

		if self.menulist:
			self["menulist"].l.setList(self.menulist)
			self["menulist"].l.setItemHeight(self.itemHeight)
			self.check = True
			self.showInfo()
			self["done_msg"].setText((_("Total") + ": %s - " + _("Exist") + ": %s - " + _("N/A") + ": %s") % (self.count_movies, count_existing, count_na))

	def showInfo(self):
		check = self["menulist"].getCurrent()
		if check == None:
			return
		if self.check:
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			#m_real_title = self["menulist"].getCurrent()[0][2]
			m_genre = self["menulist"].getCurrent()[0][3]
			#m_o_title = self["menulist"].getCurrent()[0][4]
			if os.path.exists(m_poster_path):
				DelayedFunction(500, self.poster_resize(m_poster_path))
			else:
				DelayedFunction(500, self.poster_resize(self.no_image_poster))

			self["m_info"].setText(m_title)

	def no_cover(self):
		if os.path.exists(self.no_image_poster):
			DelayedFunction(500, self.poster_resize(self.no_image_poster))

	def imdb(self):
		if self.running:
			print "EMC iMDB: Search already Running."

		elif not self.running:
			print "EMC iMDB: Search started..."
			self["done_msg"].show()
			self.no_cover()
			self.running = True
			self.counter_download = 0
			self.counter_exist = 0
			self.counter_no_poster = 0
			self.t_elapsed = 0
			self.menulist = []
			self.count_movies = len(self.m_list)
			self["exist"].setText(_("Exist: %s") % "0")
			self["no_poster"].setText(_("No Cover: %s") % "0")
			self["download"].setText(_("Download: %s") % "0")
			self["done_msg"].setText(_("Searching..."))
			self.s_supertime = time.time()
			self.cm_list = self.m_list[:]
			self.search_list = []
			self.exist_list = []
			self.check = False
			self["done_msg"].setText(_("Creating Search List.."))
			self.counting = 0
			self.count_total = len(self.cm_list)
			urls = []
			#for each in sorted(self.cm_list):
			for each in self.cm_list:
				(title, path) = each
				cover_path = re.sub(self.file_format + "$", '.jpg', path, flags=re.IGNORECASE)
				if os.path.exists(cover_path):
					self.counter_exist += 1
					self.counting += 1
					self.menulist.append(self.imdb_show(title, cover_path, _("Exist"), "", title))
					self["m_info"].setText(title)
					self["no_poster"].setText(_("No Cover: %s") % str(self.counter_no_poster))
					self["exist"].setText(_("Exist: %s") % str(self.counter_exist))
					self["download"].setText(_("Download: %s") % str(self.counter_download))
					self["menulist"].l.setList(self.menulist)
					self["menulist"].l.setItemHeight(self.itemHeight)
					self.check = True
					print "EMC iMDB: Cover vorhanden - %s" % title
				else:
					#title = getMovieNameWithoutPhrases(getMovieNameWithoutExt(title))
					s_title = getSearchList(title, None)[0]
					m_title = getSearchList(title, config.EMC.imdb.search_filter.value)[0]
					if re.search('[Ss][0-9]+[Ee][0-9]+', s_title) is not None:
						season = None
						episode = None
						seasonEpisode = re.findall('.*?[Ss]([0-9]+)[Ee]([0-9]+)', s_title, re.S|re.I)
						if seasonEpisode:
							(season, episode) = seasonEpisode[0]
						name2 = re.sub('[Ss][0-9]+[Ee][0-9]+.*[a-zA-Z0-9_]+','', s_title, flags=re.S|re.I)
						url = 'https://thetvdb.com/api/GetSeries.php?seriesname=%s&language=de' % name2.replace(' ','%20')
						urls.append(("serie", title, url, cover_path, season, episode))
					else:
						url = 'http://api.themoviedb.org/3/search/movie?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=%s&language=de' % m_title.replace(' ','%20')
						urls.append(("movie", title, url, cover_path, None, None))

			if len(urls) != 0:
				ds = defer.DeferredSemaphore(tokens=2)
				downloads = [ds.run(self.download, url).addCallback(self.parseWebpage, type, title, url, cover_path, season, episode).addErrback(self.dataError) for type, title, url, cover_path, season, episode in urls]
				finished = defer.DeferredList(downloads).addErrback(self.dataError2)
			else:
				self["done_msg"].setText(_("No Movies found!"))
				self.running = False
				self.showInfo()

	def download(self, url):
		return getPage(url, timeout=20, headers={'Accept': 'application/json'})

	def parseWebpage(self, data, type, title, url, cover_path, season, episode):
		self.counting += 1
		self.start_time = time.clock()
		if type == "movie":
			list = []
			list = re.findall('"poster_path":"\\\(.*?)".*?"original_title":"(.*?)"', data, re.S)
			if list:
				purl = "http://image.tmdb.org/t/p/%s%s" % (config.EMC.imdb.preferred_coversize.value, list[0][0])
				self.counter_download += 1
				self.end_time = time.clock()
				elapsed = (self.end_time - self.start_time) * 1000
				self.menulist.append(self.imdb_show(title, cover_path, '%.1f' %elapsed, "", title))
				if not fileExists(cover_path):
					downloadPage(purl, cover_path).addErrback(self.dataError)

				# get description
				if config.EMC.imdb.savetotxtfile.value:
					idx = []
					idx = re.findall('"id":(.*?),', data, re.S)
					if idx:
						iurl = "http://api.themoviedb.org/3/movie/%s?api_key=8789cfd3fbab7dccf1269c3d7d867aff&language=de" % idx[0]
						getPage(iurl, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.getInfos, id, type, cover_path).addErrback(self.dataError)
			else:
				self.counter_no_poster += 1
				self.menulist.append(self.imdb_show(title, cover_path, _("N/A"), "", title))

		elif type == "serie":
			list = []
			list = re.findall('<seriesid>(.*?)</seriesid>', data, re.S)
			if list:
				x = config.EMC.imdb.thetvdb_standardcover.value
				purl = "https://www.thetvdb.com/banners/_cache/posters/%s-%s.jpg" % (list[0], x)
				if x > 1 and not urlExist(purl):
					x = 1
					purl = "https://www.thetvdb.com/banners/_cache/posters/%s-%s.jpg" % (list[0], x)
				self.counter_download += 1
				self.end_time = time.clock()
				elapsed = (self.end_time - self.start_time) * 1000
				self.menulist.append(self.imdb_show(title, cover_path, '%.1f' %elapsed, "", title))
				if not fileExists(cover_path):
					downloadPage(purl, cover_path).addErrback(self.dataError)

				# get description
				if config.EMC.imdb.savetotxtfile.value:
					if season and episode:
						iurl = "https://www.thetvdb.com/api/2AAF0562E31BCEEC/series/%s/default/%s/%s/de.xml" % (list[0], str(int(season)), str(int(episode)))
						getPage(iurl, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.getInfos, id, type, cover_path).addErrback(self.dataError)
			else:
				self.counter_no_poster += 1
				self.menulist.append(self.imdb_show(title, cover_path, _("N/A"), "", title))

		self.count = ("%s: %s " + _("from") + " %s") % (self.showSearchSiteName, self.counting, self.count_total)
		self["info"].setText(self.count)
		self["no_poster"].setText(_("No Cover: %s") % str(self.counter_no_poster))
		self["exist"].setText(_("Exist: %s") % str(self.counter_exist))
		self["download"].setText(_("Download: %s") % str(self.counter_download))
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(self.itemHeight)
		self.check = True

		if self.counting == self.count_total:
			self.e_supertime = time.time()
			total_time = self.e_supertime - self.s_supertime
			avg = (total_time / self.count_total)
			self.done = ("%s " + _("movies in") + " %.1f " + _("sec found. Avg. Speed:") + " %.1f " + _("sec.")) % (self.count_total, total_time, avg)
			self["done_msg"].setText(self.done)
			self.running = False
			self.showInfo()

	def getInfos(self, data, id, type, cover_path):
		if type == "movie":
			infos = re.findall('"genres":\[(.*?)\].*?"overview":"(.*?)"', data, re.S)
			if infos:
				(genres, desc) = infos[0]
				self.writeTofile(self.decodeHtml(desc), cover_path)

		elif type == "serie":
			infos = re.findall('<Overview>(.*?)</Overview>', data, re.S)
			if infos:
				desc = infos[0]
				self.writeTofile(self.decodeHtml(desc), cover_path)

	def writeTofile(self, text, cover_path):
		print cover_path
		if not fileExists(cover_path.replace('.jpg','.txt')):
			wFile = open(cover_path.replace('.jpg','.txt'),"w")
			wFile.write(text)
			wFile.close()

	def dataError(self, error):
		print "ERROR:", error

	def dataError2(self, error):
		self.counting = int(self.counting) + 1
		print "ERROR:", error

	def errorLoad(self, error, search_title):
		print "EMC keine daten zu %s gefunden." % search_title
		#print "Please report: %s" % str(error)

	def exit(self):
		self.check = False
		if self.picload:
			del self.picload
		self.close()

	def red(self):
		if self.check:
			m_poster_path = self["menulist"].getCurrent()[0][1]
			if os.path.exists(m_poster_path):
				if m_poster_path == self.no_image_poster:
					print "EMC no_poster.jpg kann nicht geloescht werden."
				else:
					try:
						os.remove(m_poster_path)
						self.verwaltung()
						self.no_cover()
						self["done_msg"].setText(_("%s removed.") % m_poster_path)
					except:
						self["done_msg"].setText(_("%s not removed. Write protect?") % m_poster_path)

	def redLong(self):
		pass

	def ok(self):
		if self.check and self.menulist:
			data_list = []
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			data_list = [(m_title, m_poster_path)]
			self.session.openWithCallback(self.setupFinished2, getCover, data_list)

	### Cover resize ###
	def poster_resize(self, poster_path):
		if fileExists(poster_path):
			self["poster"].instance.setPixmap(gPixmapPtr())
			scale = AVSwitch().getFramebufferScale()
			size = self["poster"].instance.size()
			self.picload.setPara((size.width(), size.height(), scale[0], scale[1], False, 1, "#00000000"))
			if isDreamOS:
				if self.picload.startDecode(poster_path, False) == 0:
					ptr = self.picload.getData()
					if ptr != None:
						self["poster"].instance.setPixmap(ptr)
						self["poster"].show()
			else:
				if self.picload.startDecode(poster_path, 0, 0, False) == 0:
					ptr = self.picload.getData()
					if ptr != None:
						self["poster"].instance.setPixmap(ptr)
						self["poster"].show()

	def config(self):
		self.session.openWithCallback(self.setupFinished, imdbSetup)

	def setupFinished(self, result=False):
		print "EMC iMDB Config Saved."
		if result:
			if self.isFolder:
				self.verwaltung() #if foldercoverpath settings is changed
			self["done_msg"].show()
			self["done_msg"].setText(_("Settings have been Saved."))

	def setupFinished2(self, result):
		print "EMC iMDB single search done."
		if result:
			self.verwaltung()
			#self.showInfo()
			self["done_msg"].show()
			self["done_msg"].setText(_("Cover is Saved."))
			#DelayedFunction(3000, self["done_msg"].hide)

	def decodeHtml(self, text):
		text = text.replace('&auml;','ä')
		text = text.replace('\u00e4','ä')
		text = text.replace('&#228;','ä')

		text = text.replace('&Auml;','Ä')
		text = text.replace('\u00c4','Ä')
		text = text.replace('&#196;','Ä')

		text = text.replace('&ouml;','ö')
		text = text.replace('\u00f6','ö')
		text = text.replace('&#246;','ö')

		text = text.replace('&ouml;','Ö')
		text = text.replace('&Ouml;','Ö')
		text = text.replace('\u00d6','Ö')
		text = text.replace('&#214;','Ö')

		text = text.replace('&uuml;','ü')
		text = text.replace('\u00fc','ü')
		text = text.replace('&#252;','ü')

		text = text.replace('&Uuml;','Ü')
		text = text.replace('\u00dc','Ü')
		text = text.replace('&#220;','Ü')

		text = text.replace('&szlig;','ß')
		text = text.replace('\u00df','ß')
		text = text.replace('&#223;','ß')

		text = text.replace('&amp;','&')
		text = text.replace('&quot;','\"')
		text = text.replace('&gt;','>')
		text = text.replace('&apos;',"'")
		text = text.replace('&acute;','\'')
		text = text.replace('&ndash;','-')
		text = text.replace('&bdquo;','"')
		text = text.replace('&rdquo;','"')
		text = text.replace('&ldquo;','"')
		text = text.replace('&lsquo;','\'')
		text = text.replace('&rsquo;','\'')
		text = text.replace('&#034;','"')
		text = text.replace('&#34;','"')
		text = text.replace('&#038;','&')
		text = text.replace('&#039;','\'')
		text = text.replace('&#39;','\'')
		text = text.replace('&#160;',' ')
		text = text.replace('\u00a0',' ')
		text = text.replace('\u00b4','\'')
		text = text.replace('\u003d','=')
		text = text.replace('\u0026','&')
		text = text.replace('&#174;','')
		text = text.replace('&#225;','a')
		text = text.replace('&#233;','e')
		text = text.replace('&#243;','o')
		text = text.replace('&#8211;',"-")
		text = text.replace('&#8212;',"—")
		text = text.replace('&mdash;','—')
		text = text.replace('\u2013',"–")
		text = text.replace('&#8216;',"'")
		text = text.replace('&#8217;',"'")
		text = text.replace('&#8220;',"'")
		text = text.replace('&#8221;','"')
		text = text.replace('&#8222;',',')
		text = text.replace('\u014d','o')
		text = text.replace('\u016b','u')
		text = text.replace('\u201a','\"')
		text = text.replace('\u2018','\"')
		text = text.replace('\u201e','\"')
		text = text.replace('\u201c','\"')
		text = text.replace('\u201d','\'')
		text = text.replace('\u2019s','’')
		text = text.replace('\u00e0','à')
		text = text.replace('\u00e7','ç')
		text = text.replace('\u00e8','é')
		text = text.replace('\u00e9','é')
		text = text.replace('\u00c1','Á')
		text = text.replace('\u00c6','Æ')
		text = text.replace('\u00e1','á')

		text = text.replace('&#xC4;','Ä')
		text = text.replace('&#xD6;','Ö')
		text = text.replace('&#xDC;','Ü')
		text = text.replace('&#xE4;','ä')
		text = text.replace('&#xF6;','ö')
		text = text.replace('&#xFC;','ü')
		text = text.replace('&#xDF;','ß')
		text = text.replace('&#xE9;','é')
		text = text.replace('&#xB7;','·')
		text = text.replace("&#x27;","'")
		text = text.replace("&#x26;","&")
		text = text.replace("&#xFB;","û")
		text = text.replace("&#xF8;","ø")
		text = text.replace("&#x21;","!")
		text = text.replace("&#x3f;","?")

		text = text.replace('&#8230;','...')
		text = text.replace('\u2026','...')
		text = text.replace('&hellip;','...')

		text = text.replace('&#8234;','')
		return text

	def cleanFile(text):
		cutlist = ['x264','720p','1080p','1080i','PAL','GERMAN','ENGLiSH','WS','DVDRiP','UNRATED','RETAIL','Web-DL','DL','LD','MiC','MD','DVDR','BDRiP','BLURAY','DTS','UNCUT','ANiME',
					'AC3MD','AC3','AC3D','TS','DVDSCR','COMPLETE','INTERNAL','DTSD','XViD','DIVX','DUBBED','LINE.DUBBED','DD51','DVDR9','DVDR5','h264','AVC',
					'WEBHDTVRiP','WEBHDRiP','WEBRiP','WEBHDTV','WebHD','HDTVRiP','HDRiP','HDTV','ITUNESHD','REPACK','SYNC']
		text = text.replace('.wmv','').replace('.flv','').replace('.ts','').replace('.m2ts','').replace('.mkv','').replace('.avi','').replace('.mpeg','').replace('.mpg','').replace('.iso','')

		for word in cutlist:
			text = re.sub('(\_|\-|\.|\+)'+word+'(\_|\-|\.|\+)','+', text, flags=re.I)
		text = text.replace('.',' ').replace('-',' ').replace('_',' ').replace('+','')

	def imdb_show(self, title, pp, elapsed, genre, search_title):
		res = [ (title, pp, elapsed, genre, search_title) ]
		s1=_("Exist") + "|" + _("N/A")
		if not re.match('.*?(' + s1 + ')', elapsed):
			elapsed = "%s ms" % elapsed

		if getDesktop(0).size().width() == 1920:
			f=1.5
			gF=6
		else:
			f=1
			gF=4

		h = self.itemHeight
		if self.count_movies * h > self.listHeight:
			w = self.listWidth - 15 # place for scrollbar
		else:
			w = self.listWidth

		res.append(MultiContentEntryText(pos=(5, 0), size=(w, h), font=gF, text=search_title, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER))
		res.append(MultiContentEntryText(pos=(w-150*f, 0), size=(140*f, h), font=gF, text=elapsed, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER))
		return res

class imdbSetup(Screen, ConfigListScreenExt):
	if sz_w == 1920:
		skin = """
		<screen position="center,110" size="1800,930" title="EMC Cover search setup">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/red.png" position="10,5" size="300,70" alphatest="blend"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/green.png" position="310,5" size="300,70" alphatest="blend"/>
		<widget backgroundColor="#9f1313" font="Regular;30" halign="center" name="key_red" position="10,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
		<widget backgroundColor="#1f771f" font="Regular;30" halign="center" name="key_green" position="310,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
		<widget font="Regular;34" halign="right" position="1650,25" render="Label" size="120,40" source="global.CurrentTime">
			<convert type="ClockToText">Default</convert>
		</widget>
		<widget font="Regular;34" halign="right" position="1240,25" render="Label" size="400,40" source="global.CurrentTime" >
			<convert type="ClockToText">Date</convert>
		</widget>
		<eLabel backgroundColor="#818181" position="10,80" size="1780,1" />
		<widget enableWrapAround="1" name="config" position="10,90" itemHeight="45" scrollbarMode="showOnDemand" size="1780,810" />
		</screen>"""
	else:
		skin = """
		<screen position="center,80" size="1200,610" title="EMC Cover search setup">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/red.png" position="10,5" size="200,40" alphatest="blend"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/green.png" position="210,5" size="200,40" alphatest="blend"/>
		<widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
		<widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
		<widget source="global.CurrentTime" render="Label" position="1130,12" size="60,25" font="Regular;22" halign="right">
			<convert type="ClockToText">Default</convert>
		</widget>
		<widget source="global.CurrentTime" render="Label" position="820,12" size="300,25" font="Regular;22" halign="right">
			<convert type="ClockToText">Format:%A %d. %B</convert>
		</widget>
		<eLabel position="10,50" size="1180,1" backgroundColor="#818181" />
		<widget name="config" position="10,60" size="1180,540" itemHeight="30" enableWrapAround="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("EMC Cover search setup"))

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))

		self.configlist = []

		ConfigListScreenExt.__init__(self, self.configlist, on_change = self._onKeyChange)

		self._getConfig()

		self["actions"] = ActionMap(["SetupActions", "OkCancelActions", "EMCConfigActions"],
		{
			"cancel":	self.keyCancel,
			"red":		self.keyCancel,
			"green":	self.keySave
		}, -2)

	def _getConfig(self):
		self.configlist = []
		self.configlist.append(getConfigListEntry(_("Search Site:"), config.EMC.imdb.search, False))
		self.configlist.append(getConfigListEntry(_("Search filter for matching existing terms in the title:"), config.EMC.imdb.search_filter, False))
		self.configlist.append(getConfigListEntry(_("thetvdb cover number (standard cover):"), config.EMC.imdb.thetvdb_standardcover, False))
		self.configlist.append(getConfigListEntry(_("Preferred cover resolution (if possible):"), config.EMC.imdb.preferred_coversize, False))
		self.configlist.append(getConfigListEntry(_("Save description to movie.txt file:"), config.EMC.imdb.savetotxtfile, False))
		self.configlist.append(getConfigListEntry(_("Single Search:"), config.EMC.imdb.singlesearch, True))
		self.configlist.append(getConfigListEntry(_("Search filter for matching existing terms in the title:"), config.EMC.imdb.singlesearch_filter, False))
		if config.EMC.imdb.singlesearch.value not in ('2','3'):
			itext = ""
			if config.EMC.imdb.singlesearch.value not in ('0','4'):
				itext = _(" (without counting cover range)")
				self.configlist.append(getConfigListEntry(_("thetvdb cover range per title:"), config.EMC.imdb.singlesearch_tvdbcoverrange, False))
			self.configlist.append(getConfigListEntry(_("Search Results per Search Site%s:") %itext, config.EMC.imdb.singlesearch_siteresults, False))
		self.configlist.append(getConfigListEntry(_("Set path to save the folder Cover:"), config.EMC.imdb.singlesearch_foldercoverpath, False))

		self["config"].list = self.configlist
		self["config"].setList(self.configlist)

	def _onKeyChange(self):
		try:
			cur = self["config"].getCurrent()
			if cur and cur[2]:
				self._getConfig()
		except:
			pass

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close(True)

	def keyClose(self):
		self.close()

class getCover(Screen):
	if sz_w == 1920:
		skin = """
		<screen position="center,110" size="1800,930" title="EMC Cover Selecter">
		<widget name="m_info" position="10,10" size="1780,40" font="Regular;35" halign="center" foregroundColor="yellow"/>
		<eLabel backgroundColor="#818181" position="10,60" size="1780,1" />
		<widget name="poster" position="10,80" size="400,600" alphatest="blend"/>
		<widget name="menulist" position="440,80" size="1350,810" itemHeight="45" scrollbarMode="showOnDemand" enableWrapAround="1"/>
		<widget name="info" position="10,700" size="400,140" font="Regular;30" halign="center" valign="center" foregroundColor="yellow"/>
		</screen>"""
	else:
		skin = """
   		<screen position="center,80" size="1200,610" title="EMC Cover Selecter">
		<widget name="m_info" position="10,5" size="1180,30" font="Regular;24" halign="center" valign="center" foregroundColor="yellow"/>
		<eLabel backgroundColor="#818181" position="10,40" size="1180,1" />
		<widget name="poster" position="20,50" size="220,330" alphatest="blend"/>
		<widget name="menulist" position="270,50" size="920,540" itemHeight="30" scrollbarMode="showOnDemand" enableWrapAround="1"/>
		<widget name="info" position="10,400" size="220,80" font="Regular;20" halign="center" valign="center" foregroundColor="yellow"/>
		</screen>"""

	def __init__(self, session, data):
		Screen.__init__(self, session, data)

		self["actions"] = HelpableActionMap(self, "EMCimdb",
		{
			"EMCEXIT":	self.exit,
			#"green":	self.keySave,
			#"cancel":	self.keyClose,
			"EMCOK":	self.ok,
		}, -1)

		(title, o_path) = data.pop()
		self.m_title = title
		self["m_info"] = Label(("%s") % self.m_title)
		self.o_path = o_path
		self.menulist = []
		self["menulist"] = imdblist([])
		self["poster"] = Pixmap()
		self["info"] = Label(_("Searching for %s") % self.m_title)
		self["menulist"].onSelectionChanged.append(self.showInfo)
		self.check = False
		self.path = "/tmp/tmp.jpg"
		self.cover_count = 0
		self.einzel_start_time = time.time()

		self.picload = ePicLoad()
		#self.picload_conn = self.picload.PictureData.connect(self.showCoverCallback)
		#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.listWidth = self["menulist"].instance.size().width()
		self.listHeight = self["menulist"].instance.size().height()
		self.itemHeight = self["menulist"].l.getItemSize().height()
		self.setTitle(_("EMC Cover Selecter"))

		if config.EMC.imdb.singlesearch.value == "0":
			self.searchimdb(self.m_title)
		elif config.EMC.imdb.singlesearch.value == "1":
			self.searchtvdb(self.m_title)
		elif config.EMC.imdb.singlesearch.value == "2":
			self.searchcsfd(self.m_title)
		elif config.EMC.imdb.singlesearch.value == "3":
			self.searchimdb(self.m_title)
			self.searchtmdb(self.m_title)
			self.searchtvdb(self.m_title)
			self.searchcsfd(self.m_title)
		elif config.EMC.imdb.singlesearch.value == "4":
			self.searchtmdb(self.m_title)
		elif config.EMC.imdb.singlesearch.value == "5":
			self.searchtmdb(self.m_title)
			self.searchtvdb(self.m_title)
		elif config.EMC.imdb.singlesearch.value == "6":
			self.searchtmdb(self.m_title)
			self.searchtvdb(self.m_title)
			self.searchimdb(self.m_title)

	def showCovers_adddetail_csfd(self, data, title):
		title_s = re.findall('<title>(.*?)\|', data, re.S)
		if title_s:
			if title_s[0] != "Vyhled\xc3\xa1v\xc3\xa1n\xc3\xad ":
				csfd_title = title_s[0]
			else:
				csfd_title = title
			print "EMC csfd: Movie name - %s" % csfd_title
		else:
			csfd_title = title
		bild = re.findall('<img src="(//img.csfd.cz/files/images/film/posters/.*?|//img.csfd.cz/posters/.*?)" alt="poster"', data, re.DOTALL | re.IGNORECASE)
		if bild:
			print "EMC csfd: Cover Select - %s" % title
			self.cover_count += 1
			csfd_url = "http:" + bild[0].replace('\\','').strip()
			self.menulist.append(self.showCoverlist(csfd_title, csfd_url, self.o_path, "csfd: "))
			#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
			bild = re.findall('<h3>Plak.*?ty</h3>(.*?)</table>', data, re.S)
			if bild:
				bild1 = re.findall('style=\"background-image\: url\(\'(.*?)\'\)\;', bild[0], re.DOTALL | re.IGNORECASE)
				if bild1:
					for each in bild1:
						print "EMC csfd: Cover Select - %s" % title
						self.cover_count += 1
						csfd_url = "http:" + each.replace('\\','').strip()
						self.menulist.append(self.showCoverlist(csfd_title, csfd_url, self.o_path, "csfd: "))
						#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
				else:
					print "EMC csfd 3 : no else covers - %s" % title
			else:
				print "EMC csfd 2 : no else covers - %s" % title
		else:
			print "EMC csfd 1 : keine infos gefunden - %s" % title

	@defer.inlineCallbacks
	def searchcsfd(self, title):
		print "EMC csfd - searchcsfd: ", title
		part = getSearchList(title, config.EMC.imdb.singlesearch_filter.value)[0]
		search_title = urllib.quote(part)
		url = "http://www.csfd.cz/hledat/?q=%s" % search_title
		data = yield getPage(url).addErrback(self.errorLoad, title)
		bild = re.findall('<img src=\"(//img.csfd.cz/files/images/film/posters/.*?|//img.csfd.cz/posters/.*?)\".*?<h3 class="subject"><a href="(.*?)" class="film c.">(.*?)</a>.*?</li>', data, re.DOTALL | re.IGNORECASE)
		if bild:
			for each in bild:
				print "EMC csfd: Cover Select - %s" % title
				self.cover_count += 1
				csfd_title = each[2]
				csfd_detail_url = "http://www.csfd.cz" + each[1]
				csfd_url = "http:" + each[0]
				self.menulist.append(self.showCoverlist(csfd_title, csfd_url, self.o_path, 'csfd: '))
				data1 = yield getPage(csfd_detail_url).addErrback(self.errorLoad, csfd_title)
				self.showCovers_adddetail_csfd(data1, csfd_title)
				#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		else:
			self.showCovers_adddetail_csfd(data, title)
			#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		self.search_done()

	@defer.inlineCallbacks
	def searchtmdb(self, title):
		print "EMC TMDB: Cover Select - %s" % title
		templist = []
		coverlist = []
		coversize = config.EMC.imdb.preferred_coversize.value
		if config.EMC.imdb.singlesearch.value != '3':
			finish = False
			siteresults = int(config.EMC.imdb.singlesearch_siteresults.value)
			part = getSearchList(title, config.EMC.imdb.singlesearch_filter.value)
			for item in part:
				if finish:
					break
				url = 'http://api.themoviedb.org/3/search/movie?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=%s&language=de' % item.replace(' ','%20')
				data = yield getPage(url).addErrback(self.errorLoad, title)
				if data:
					bild = re.findall('"poster_path":"\\\(.*?)".*?"original_title":"(.*?)"', data, re.S)
					if bild:
						for each in bild:
							m_cover = each[0]
							m_title = each[1]
							if m_cover in coverlist:
								continue
							coverlist.append(m_cover)
							self.cover_count += 1
							tmdb_url = "http://image.tmdb.org/t/p/%s%s" % (coversize, m_cover)
							templist.append(self.showCoverlist(m_title, tmdb_url, self.o_path, "tmdb: "))
							if siteresults and len(coverlist) >= siteresults:
								finish = True
								break
			templist.sort()
			self.menulist.extend(templist)
			#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		else:
			part = getSearchList(title, config.EMC.imdb.singlesearch_filter.value)[0]
			url = 'http://api.themoviedb.org/3/search/movie?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=%s&language=de' % part.replace(' ','%20')
			data = yield getPage(url).addErrback(self.errorLoad, title)
			if data:
				bild = re.findall('"poster_path":"\\\(.*?)".*?"original_title":"(.*?)"', data, re.S)
				if bild:
					for each in bild:
						m_cover = each[0]
						m_title = each[1]
						if m_cover in coverlist:
							continue
						coverlist.append(m_cover)
						self.cover_count += 1
						tmdb_url = "http://image.tmdb.org/t/p/%s%s" % (coversize, m_cover)
						templist.append(self.showCoverlist(m_title, tmdb_url, self.o_path, "tmdb: "))
			templist.sort()
			self.menulist.extend(templist)
			#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		if not templist:
			#self["info"].setText(_("Nothing found for %s") % title)
			print "EMC TMDB: keine infos gefunden - %s" % title
		self.search_done()

	@defer.inlineCallbacks
	def searchtvdb(self, title):
		print "EMC TVDB: Cover Select - %s" % title
		templist = []
		coverlist = []
		standardcover = config.EMC.imdb.thetvdb_standardcover.value
		if config.EMC.imdb.singlesearch.value != '3':
			finish = False
			coverrange = int(config.EMC.imdb.singlesearch_tvdbcoverrange.value)
			siteresults = int(config.EMC.imdb.singlesearch_siteresults.value)
			part = getSearchList(title, config.EMC.imdb.singlesearch_filter.value)
			for item in part:
				if finish:
					break
				url = "https://www.thetvdb.com/api/GetSeries.php?seriesname=%s&language=de" % item.replace(' ','%20')
				data = yield getPage(url).addErrback(self.errorLoad, title)
				if data:
					id = re.findall('<seriesid>(.*?)</seriesid>.*?<SeriesName>(.*?)</SeriesName>', data, re.S)
					if id:
						for each in id:
							if finish:
								break
							m_cover = each[0]
							m_title = each[1]
							if not m_cover or m_cover in coverlist or '403:' in m_title:
								continue
							coverlist.append(m_cover)
							if coverrange == 1:
								x = standardcover
								tvdb_url = "https://www.thetvdb.com/banners/_cache/posters/%s-%s.jpg" % (m_cover, x)
								if x > 1 and not urlExist(tvdb_url):
									x = 1
									tvdb_url = "https://www.thetvdb.com/banners/_cache/posters/%s-%s.jpg" % (m_cover, x)
								self.cover_count += 1
								templist.append(self.showCoverlist(m_title, tvdb_url, self.o_path, "tvdb: cover-%s : " %x))
							else:
								x = 0
								while True:
									x += 1
									tvdb_url = "https://www.thetvdb.com/banners/_cache/posters/%s-%s.jpg" % (m_cover, x)
									if x > 1 and (coverrange and x > coverrange or not urlExist(tvdb_url)):
										break
									self.cover_count += 1
									templist.append(self.showCoverlist(m_title, tvdb_url, self.o_path, "tvdb: cover-%s : " %x))
							if siteresults and len(coverlist) >= siteresults:
								finish = True
								break
			self.menulist.extend(templist)
			#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		else:
			part = getSearchList(title, config.EMC.imdb.singlesearch_filter.value)[0]
			url = "https://www.thetvdb.com/api/GetSeries.php?seriesname=%s&language=de" % part.replace(' ','%20')
			data = yield getPage(url).addErrback(self.errorLoad, title)
			if data:
				id = re.findall('<seriesid>(.*?)</seriesid>.*?<SeriesName>(.*?)</SeriesName>', data, re.S)
				if id:
					for each in id:
						m_cover = each[0]
						m_title = each[1]
						if not m_cover or m_cover in coverlist or '403:' in m_title:
							continue
						coverlist.append(m_cover)
						x = standardcover
						tvdb_url = "https://www.thetvdb.com/banners/_cache/posters/%s-%s.jpg" % (m_cover, x)
						if x > 1 and not urlExist(tvdb_url):
							x = 1
							tvdb_url = "https://www.thetvdb.com/banners/_cache/posters/%s-%s.jpg" % (m_cover, x)
						self.cover_count += 1
						templist.append(self.showCoverlist(m_title, tvdb_url, self.o_path, "tvdb: "))
			templist.sort()
			self.menulist.extend(templist)
			#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		if not templist:
			#self["info"].setText(_("Nothing found for %s") % title)
			print "EMC TVDB: keine infos gefunden - %s" % title
		self.search_done()

	@defer.inlineCallbacks
	def searchimdb(self, title):
		print "EMC IMDB: Cover Select - %s" % title
		templist = []
		coverlist = []
		coversize = config.EMC.imdb.preferred_coversize.value.replace('w','SX')
		if config.EMC.imdb.singlesearch.value != '3':
			finish = False
			siteresults = int(config.EMC.imdb.singlesearch_siteresults.value)
			part = getSearchList(title, config.EMC.imdb.singlesearch_filter.value)
			for item in part:
				if finish:
					break
				url = 'http://m.imdb.com/find?q=%s' % item.replace(' ','%20')
				data = yield getPage(url).addErrback(self.errorLoad, title)
				if data:
					bild = re.findall('<div class="poster.*?<img src="https://images-na.ssl-images-amazon.com/images(.*?)V1.*?<a href="/title/.*?">(.*?)</a>', data, re.S)
					if bild:
						for each in bild:
							m_cover = each[0]
							m_title = each[1]
							if m_cover in coverlist:
								continue
							coverlist.append(m_cover)
							self.cover_count += 1
							imdb_url = "https://images-na.ssl-images-amazon.com/images%sV1_%s.jpg" % (m_cover, coversize)
							templist.append(self.showCoverlist(m_title, imdb_url, self.o_path, "imdb: "))
							if siteresults and len(coverlist) >= siteresults:
								finish = True
								break
			templist.sort()
			self.menulist.extend(templist)
			#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		else:
			part = getSearchList(title, config.EMC.imdb.singlesearch_filter.value)[0]
			url = 'http://m.imdb.com/find?q=%s' % part.replace(' ','%20')
			data = yield getPage(url).addErrback(self.errorLoad, title)
			if data:
				bild = re.findall('<div class="poster.*?<img src="https://images-na.ssl-images-amazon.com/images(.*?)V1.*?<a href="/title/.*?">(.*?)</a>', data, re.S)
				if bild:
					for each in bild:
						m_cover = each[0]
						m_title = each[1]
						if m_cover in coverlist:
							continue
						coverlist.append(m_cover)
						self.cover_count += 1
						imdb_url = "https://images-na.ssl-images-amazon.com/images%sV1_%s.jpg" % (m_cover, coversize)
						templist.append(self.showCoverlist(m_title, imdb_url, self.o_path, "imdb: "))
			templist.sort()
			self.menulist.extend(templist)
			#self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		if not templist:
			#self["info"].setText(_("Nothing found for %s") % title)
			print "EMC TMDB: keine infos gefunden - %s" % title
		self.search_done()

	def errorLoad(self, error, title):
		print "EMC keine daten zu %s gefunden." % title
		print error

	def search_done(self):
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(self.itemHeight)
		self.check = True
		self.showInfo()
		self["info"].setText((_("found") + " %s " + _("covers in") + " %.1f " + _("sec")) % (self.cover_count, (time.time() - self.einzel_start_time)))

	def showInfo(self):
		if self.check and self.menulist:
			m_title = self["menulist"].getCurrent()[0][0]
			m_url = self["menulist"].getCurrent()[0][1]
			if m_url:
				#m_url = re.findall('(.*?)\.', m_url)
				#extra_imdb_convert = "._V1_SX320.jpg"
				#m_url = "http://ia.media-imdb.com/images/%s%s" % (m_url[0], extra_imdb_convert)
				print "EMC iMDB: Download Poster - %s" % m_url
				try:
					req = requests.session()
					r = req.get(m_url, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36'})
					f = open(self.path, 'wb')
					for chunk in r.iter_content(chunk_size=512 * 1024):
						if chunk:
							f.write(chunk)
					f.close()
					if os.path.exists(self.path):
						self.poster_resize(self.path, m_title)
						#ptr = LoadPixmap(self.path)
						#if ptr is None:
						#        ptr = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png")
						#        print "EMC iMDB: Load default NO Poster."
						#if ptr is not None:
						#        self["poster"].instance.setPixmap(ptr)
						#        print "EMC iMDB: Load Poster - %s" % m_title
					else:
						print "EMC iMDB: No url found for - %s" % m_title
				except:
					pass
			else:
				print "EMC iMDB: No url found for - %s" % m_title

	def poster_resize(self, poster_path, m_title):
		self.m_title = m_title
		self["poster"].instance.setPixmap(gPixmapPtr())
		self["poster"].hide()
		sc = AVSwitch().getFramebufferScale() # Maybe save during init
		size = self["poster"].instance.size()
		if self.picload:
			self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, "#00000000")) # Background dynamically
			#self.picload.startDecode(poster_path)
			if isDreamOS:
				result = self.picload.startDecode(poster_path, False)
			else:
				result = self.picload.startDecode(poster_path, 0, 0, False)
			if result == 0:
				#def showCoverCallback(self, picInfo=None):
				#if picInfo:
				ptr = self.picload.getData()
				if ptr != None:
					print "EMC iMDB: Load Poster - %s" % self.m_title
					self["poster"].instance.setPixmap(ptr)
					self["poster"].show()

	def exit(self):
		if self.picload:
			del self.picload
		self.check = False
		self.close(False)

	def ok(self, choose=False):
		movie_homepath = os.path.realpath(config.EMC.movie_homepath.value)
		if choose:
			self.chooseDirectory(movie_homepath)
		if self.check and self.menulist:
			try:
				shutil.move(self.path, self.o_path)
				print "EMC iMDB: mv poster to real path - %s %s" % (self.path, self.o_path)
				self.check = False
				self.close(True)
			except Exception, e:
				print('[EMCCoverSearch] save Cover execute get failed: ', str(e))
				try:
					self.session.openWithCallback(self.saveCoverHomepath, MessageBox, _("Can not save " + self.o_path + " !\n Save Cover now in " + movie_homepath + " ?"), MessageBox.TYPE_YESNO, 10)
				except Exception, e:
					print('[EMCCoverSearch] save Cover in homepath execute get failed: ', str(e))

	def saveCoverHomepath(self, result):
		if result:
			movie_homepath = os.path.realpath(config.EMC.movie_homepath.value)
			try:
				shutil.move(self.path, movie_homepath + "/" + self.o_path.replace(self.o_path[:-len(self.o_path) + self.o_path.rfind('/') + 1],''))
				self.check = False
				self.close(True)
			except Exception, e:
				print('[EMCCoverSearch] saveCoverHomepath execute get failed: ', str(e))
				try:
					self.session.openWithCallback(self.chooseCallback, MessageBox, _("Can not save Cover in " + movie_homepath + " !\n\n Now you can select another folder to save the Cover."), MessageBox.TYPE_YESNO, 10)
				except Exception, e:
					print('[EMCCoverSearch] save Cover get failed: ', str(e))
		else:
			self.check = False
			self.close(False)

	def chooseCallback(self, result):
		if result:
			self.check = False
			self.ok(True)
		else:
			self.check = False
			self.close(False)

	def chooseDirectory(self, choosePath):
		if choosePath is not None:
			self.session.openWithCallback(
					self.moveCoverTo,
					LocationBox,
						windowTitle = _("Move Cover to:"),
						text = _("Choose directory"),
						currDir = str(choosePath)+"/",
						bookmarks = config.movielist.videodirs,
						autoAdd = False,
						editDir = True,
						inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/proc", "/run", "/sbin", "/sys", "/usr", "/var"],
						minFree = 100 )

	def moveCoverTo(self, targetPath):
		if targetPath is not None:
			try:
				shutil.move(self.path, targetPath + "/" + self.o_path.replace(self.o_path[:-len(self.o_path) + self.o_path.rfind('/') + 1],''))
				self.check = False
				self.close(True)
			except Exception, e:
				print('[EMCCoverSearch] moveCoverTo execute get failed: ', str(e))
				self.chooseDirectory(targetPath)
		else:
			self.check = False
			self.close(False)

	def showCoverlist(self, title, url, path, art):
		res = [ (title, url, path) ]
		title = art + title

		if getDesktop(0).size().width() == 1920:
			f=1.5
			gF=6
		else:
			f=1
			gF=4

		h = self.itemHeight
		if self.cover_count * h > self.listHeight:
			w = self.listWidth - 15 # place for scrollbar
		else:
			w = self.listWidth

		res.append(MultiContentEntryText(pos=(0, 0), size=(w, h), font=gF, text=title, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER))
		return res
