#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Copyright 2011 Gimick bbtgaf@googlemail.com
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as published by
#the Free Software Foundation, version 3 of the License.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU Affero General Public License
#along with this program. If not, see <http://www.gnu.org/licenses/>.
#In the "official" distribution you can find the license in agpl-3.0.txt.

"""
Attempt to detect which poker sites are installed by the user, their
 heroname and the path to the HH files.

This is intended for new fpdb users to get them up and running quickly.

We assume that the majority of these users will install the poker client
into default locations so we will only check those places.

We just look for a hero HH folder, and don't really care if the
  application is installed

Situations not handled are:
    Multiple screennames using the computer
    TODO Unexpected dirs in HH dir (e.g. "archive" may become a heroname!)
    Non-standard installation locations
    TODO Mac installations

Typical Usage:
    See TestDetectInstalledSites.py

Todo:
    replace hardcoded site list with something more subtle

"""
import platform
import os

if platform.system() == 'Windows':
    from win32com.shell import shellcon
    from win32com.shell import shell
    PROGRAM_FILES = unicode(shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAM_FILES, 0, 0))
    LOCAL_APPDATA = unicode(shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, 0, 0))

class DetectInstalledSites():

    def __init__(self, site = "All"):
        #
        # objects returned
        #
        self.sitestatusdict = {}
        self.sitecode = site
        self.heroname = ""
        self.hhpath = ""
        self.detected = ""
        #
        #since each site has to be hand-coded in this module, there
        #is little advantage in querying the sites table at the moment.
        #plus we can run from the command line as no dependencies
        #
        self.supportedSites = { "FT" : "Full Tilt Poker",
                                "PS" : "PokerStars",
                                "EV" : "Everleaf",
                                "W2" : "Win2day",
                                "OG" : "OnGame",
                                "UB" : "UltimateBet",
                                "BF" : "Betfair",
                                "AB" : "Absolute",
                                "PP" : "PartyPoker",
                                "P8" : "PacificPoker",
                                "PA" : "Partouche",
                                "CA" : "Carbon",
                                "PK" : "PKR",
                                "IP" : "iPoker",
                                "WM" : "Winamax",
                                "EP" : "Everest" }
                            
        self.supportedPlatforms = ["Linux", "XP", "Win7"]
        #
        #detect os in use - we will work with "Linux", "XP" and "Win7"
        #    Vista will be considered as Win7
        #
        self.userPlatform = platform.system()  #Linux, Windows,
        if self.userPlatform == 'Windows':
            self.userPlatform = platform.release() # XP or various strings for Vista/win7
            if self.userPlatform <> 'XP':
                self.userPlatform = 'Win7' #Vista and win7

        if site == "All":
            for siteiter in self.supportedSites:
                self.sitestatusdict[siteiter]=self.Detect(siteiter)
        else:
            self.sitestatusdict[site]=self.Detect(site)
            self.heroname = self.sitestatusdict[site]['heroname']
            self.hhpath = self.sitestatusdict[site]['hhpath']
            self.detected = self.sitestatusdict[site]['detected']
            
        return

    def Detect(self, siteToDetect):

        self.pathfound = ""
        self.herofound = ""
        
        if siteToDetect == "FT":
            self.FT()
        elif siteToDetect == "PS":
            self.PS()
            
        if (self.pathfound and self.herofound):
            self.pathfound = unicode(self.pathfound)
            self.herofound = unicode(self.herofound)
            return {"detected":True, "hhpath":self.pathfound, "heroname":self.herofound}
        else:
            return {"detected":False, "hhpath":"", "heroname":""}
            
    def FT(self):

        if self.userPlatform == "Linux":
            hhp=os.path.expanduser("~/.wine/drive_c/Program Files/Full Tilt Poker/HandHistory/")
        elif self.userPlatform == "XP":
            hhp=os.path.expanduser(PROGRAM_FILES+"\\Full Tilt Poker\\HandHistory\\")
        elif self.userPlatform == "Win7":
            hhp=os.path.expanduser(PROGRAM_FILES+"\\Full Tilt Poker\\HandHistory\\")
        else:
            return
            
        if os.path.exists(hhp):
                self.pathfound = hhp
        try:
            self.herofound = os.listdir(self.pathfound)[0]
            self.pathfound = self.pathfound + self.herofound
        except:
            pass
 
        return
        
    def PS(self):

        if self.userPlatform == "Linux":
            hhp=os.path.expanduser("~/.wine/drive_c/Program Files/PokerStars/HandHistory/")
        elif self.userPlatform == "XP":
            hhp=os.path.expanduser(PROGRAM_FILES+"\\PokerStars\\HandHistory\\")
        elif self.userPlatform == "Win7":
            hhp=os.path.expanduser(LOCAL_APPDATA+"\\PokerStars\\HandHistory\\")
        else:
            return
            
        if os.path.exists(hhp):
                self.pathfound = hhp
        try:
            self.herofound = os.listdir(self.pathfound)[0]
            self.pathfound = self.pathfound + self.herofound
        except:
            pass
            
        return
        
 
