#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Copyright 2009-2011, Grigorij Indigirkin
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
########################################################################

import L10n
_ = L10n.get_translation()

import sys
from collections import defaultdict

from Configuration import LOCALE_ENCODING
from Exceptions import FpdbParseError
from HandHistoryConverter import *

# PartyPoker HH Format

class PartyPoker(HandHistoryConverter):
    sitename = "PartyPoker"
    codepage = ("utf8", "cp1252")
    siteId = 9
    filetype = "text"
    sym        = {'USD': "\$", 'EUR': u"\u20ac", 'T$': ""}
    currencies = {"\$": "USD", "$": "USD", u"\xe2\x82\xac": "EUR", u"\u20ac": "EUR", '': "T$"}
    substitutions = {
                     'LEGAL_ISO' : "USD|EUR",            # legal ISO currency codes
                            'LS' : u"\$|\u20ac|\xe2\x82\xac|",    # Currency symbols - Euro(cp1252, utf-8)
                           'NUM' : u".,\d",
                    }
    limits = { 'NL':'nl', 'PL':'pl', '':'fl', 'FL':'fl' }
    games = {                         # base, category
                   "Texas Hold'em" : ('hold','holdem'),
                           'Omaha' : ('hold','omahahi'),
                     'Omaha Hi-Lo' : ('hold','omahahilo'),
               "7 Card Stud Hi-Lo" : ('stud','studhilo'),
                     "7 Card Stud" : ('stud','studhi'),
                  "Double Hold'em" : ('hold','2_holdem'),
            }

    Lim_Blinds = {  '0.04': ('0.01', '0.02'),        '0.08': ('0.02', '0.04'),
                        '0.10': ('0.02', '0.05'),    '0.20': ('0.05', '0.10'),
                        '0.30': ('0.07', '0.15'),    '0.50': ('0.10', '0.25'),
                        '1.00': ('0.25', '0.50'),       '1': ('0.25', '0.50'),
                        '2.00': ('0.50', '1.00'),       '2': ('0.50', '1.00'),
                        '4.00': ('1.00', '2.00'),       '4': ('1.00', '2.00'),
                        '6.00': ('1.00', '3.00'),       '6': ('1.00', '3.00'),
                        '8.00': ('2.00', '4.00'),       '8': ('2.00', '4.00'),
                       '10.00': ('2.00', '5.00'),      '10': ('2.00', '5.00'),
                       '12.00': ('3.00', '6.00'),      '12': ('3.00', '6.00'),
                       '20.00': ('5.00', '10.00'),     '20': ('5.00', '10.00'),
                       '30.00': ('10.00', '15.00'),    '30': ('10.00', '15.00'),
                       '40.00': ('10.00', '20.00'),    '40': ('10.00', '20.00'),
                       '60.00': ('15.00', '30.00'),    '60': ('15.00', '30.00'),
                      '100.00': ('25.00', '50.00'),   '100': ('25.00', '50.00'),
                      '200.00': ('50.00', '100.00'),  '200': ('50.00', '100.00'),
                      '500.00': ('125.00', '250.00'), '500': ('125.00', '250.00'),
                  }
    NLim_Blinds_20bb = {    '0.80': ('0.01', '0.02'),
                            '1.60': ('0.02', '0.04'),
                            '4': ('0.05', '0.10'),
                            '10': ('0.10', '0.25'),
                            '20': ('0.25', '0.50'),
                            '40': ('0.50', '1.00'),
                            '240': ('3.00', '6.00'),
                            #'10': ('0.10', '0.25'),
                            #'10': ('0.10', '0.25'),
                            #'10': ('0.10', '0.25'),
                            #'10': ('0.10', '0.25'),
                       }

    months = { 'January':1, 'Jan':1, 'February':2, 'Feb':2, 'March':3, 'Mar':3,
                 'April':4, 'Apr':4, 'May':5, 'May':5, 'June':6, 'Jun':6,
                  'July':7, 'Jul':7, 'August':8, 'Aug':8, 'September':9, 'Sep':9,
               'October':10, 'Oct':10, 'November':11, 'Nov':11, 'December':12, 'Dec':12}

    # Static regexes
    re_GameInfo = re.compile(u"""
            \*{5}\sHand\sHistory\s(F|f)or\sGame\s(?P<HID>\d+)\s\*{5}\s+
            ((?P<CURRENCY>[%(LS)s]))?\s*
            (
             ([%(LS)s]?(?P<SB>[%(NUM)s]+)/[%(LS)s]?(?P<BB>[%(NUM)s]+)\s*(?:%(LEGAL_ISO)s)?\s+((?P<LIMIT3>NL|PL|FL|)\s+)?)|
             ((?P<CASHBI>[%(NUM)s]+)\s(?:%(LEGAL_ISO)s)?\s*)(?P<LIMIT2>(NL|PL|FL|))?\s*
            )
            (Tourney\s*)?
            (?P<GAME>(Texas\sHold\'em|Omaha\sHi-Lo|Omaha|7\sCard\sStud\sHi-Lo|7\sCard\sStud|Double\sHold\'em))\s*
            (Game\sTable\s*)?
            (
             (\((?P<LIMIT>(NL|PL|FL|))\)\s*)?
             (\(STT\sTournament\s\#(?P<TOURNO>\d+)\)\s*)?
            )?
            \s*-\s*
            (?P<DATETIME>.+)
            """ % substitutions, re.VERBOSE | re.UNICODE)

    re_HandInfo     = re.compile("""
            ^Table\s(?P<TABLE>.+?)?\s+
            ((?: \#|\(|)(?P<TABLENO>\d+)\)?\s+)?
            (\(No\sDP\)\s)?
            \(\s?(?P<PLAY>Real|Play)\s+Money\s?\)\s+(--\s*)? # FIXME: check if play money is correct
            Seat\s+(?P<BUTTON>\d+)\sis\sthe\sbutton
            \s+Total\s+number\s+of\s+players\s+\:\s+(?P<PLYRS>\d+)/?(?P<MAX>\d+)?
            """, re.VERBOSE|re.MULTILINE|re.DOTALL)

    re_GameInfoTrny     = re.compile("""
            \*{5}\sHand\sHistory\s(F|f)or\sGame\s(?P<HID>\d+)\s\*{5}\s+
            (?P<LIMIT>(NL|PL|FL|))\s*
            (?P<GAME>(Texas\sHold\'em|Omaha\sHi-Lo|Omaha|7\sCard\sStud\sHi-Lo|7\sCard\sStud|Double\sHold\'em))\s+
            (?:(?P<BUYIN>[%(LS)s]?[%(NUM)s]+)\s*(?P<BUYIN_CURRENCY>%(LEGAL_ISO)s)?\s*Buy-in\s+)?
            Trny:\s?(?P<TOURNO>\d+)\s+
            Level:\s*(?P<LEVEL>\d+)\s+
            ((Blinds|Stakes)(?:-Antes)?)\(
                (?P<SB>[%(NUM)s ]+)\s*
                /(?P<BB>[%(NUM)s ]+)
                (?:\s*-\s*(?P<ANTE>[%(NUM)s ]+)\$?)?
            \)
            \s*\-\s*
            (?P<DATETIME>.+)
            """ % substitutions, re.VERBOSE | re.UNICODE)

    re_PlayerInfo   = re.compile(u"""
          (S|s)eat\s(?P<SEAT>\d+):\s
          (?P<PNAME>.*)\s
          \(\s*[%(LS)s]?(?P<CASH>[%(NUM)s]+)\s*(?:%(LEGAL_ISO)s|)\s*\)
          """ % substitutions, re.VERBOSE| re.UNICODE)

    re_NewLevel = re.compile(u"^Blinds(-Antes)?\((?P<SB>[%(NUM)s ]+)/(?P<BB>[%(NUM)s ]+)(?:\s*-\s*(?P<ANTE>[%(NUM)s ]+))?\)" % substitutions, re.VERBOSE|re.MULTILINE|re.DOTALL)
    re_CountedSeats = re.compile("^Total\s+number\s+of\s+players\s*:\s*(?P<COUNTED_SEATS>\d+)", re.MULTILINE)
    re_Identify     = re.compile(u'\*{5}\sHand\sHistory\s[fF]or\sGame\s\d+\s')
    re_SplitHands   = re.compile('\n\n+')
    re_TailSplitHands   = re.compile('(\x00+)')
    lineSplitter    = '\n'
    re_Button       = re.compile('Seat (?P<BUTTON>\d+) is the button', re.MULTILINE)
    re_Board        = re.compile(r"\[(?P<CARDS>.+)\]")
    re_NoSmallBlind = re.compile(
                    '^There is no Small Blind in this hand as the Big Blind '
                    'of the previous hand left the table', re.MULTILINE)
    re_20BBmin       = re.compile(r"Table 20BB Min")
    re_Cancelled     = re.compile('Table\sClosed\s?', re.MULTILINE)
    re_Disconnected  = re.compile('Connection\sLost\sdue\sto\ssome\sreason\s?', re.MULTILINE)
    re_GameStartLine = re.compile('Game\s\#\d+\sstarts', re.MULTILINE)
    re_PreliminaryHand = re.compile(r"Buy-in  - ")

    def allHandsAsList(self):
        list = HandHistoryConverter.allHandsAsList(self)
        if list is None:
            return []
        return filter(lambda text: len(text.strip()), list)

    def compilePlayerRegexs(self,  hand):
        players = set([player[1] for player in hand.players])
        if not players <= self.compiledPlayers: # x <= y means 'x is subset of y'
            self.compiledPlayers = players
            player_re = "(?P<PNAME>" + "|".join(map(re.escape, players)) + ")"
            subst = {'PLYR': player_re, 'CUR_SYM': self.sym[hand.gametype['currency']],
                'CUR': hand.gametype['currency'] if hand.gametype['currency']!='T$' else '(chips|)',
                'BRAX' : u"\[\(\)\]"
                    }
            self.re_PostSB = re.compile(
                r"%(PLYR)s posts small blind [%(BRAX)s]?%(CUR_SYM)s(?P<SB>[.,0-9]+) ?%(CUR)s[%(BRAX)s]?\."
                %  subst, re.MULTILINE)
            self.re_PostBB = re.compile(
                r"%(PLYR)s posts big blind [%(BRAX)s]?%(CUR_SYM)s(?P<BB>[.,0-9]+) ?%(CUR)s[%(BRAX)s]?\."
                %  subst, re.MULTILINE)
            self.re_PostDead = re.compile(
                r"%(PLYR)s posts big blind \+ dead [%(BRAX)s]?%(CUR_SYM)s?(?P<BBNDEAD>[.,0-9]+) ?%(CUR_SYM)s?[%(BRAX)s]?\." %  subst,
                re.MULTILINE)
            self.re_Antes = re.compile(
                r"%(PLYR)s posts ante [%(BRAX)s]?%(CUR_SYM)s(?P<ANTE>[.,0-9]+) ?%(CUR)s[%(BRAX)s]?" %  subst,
                re.MULTILINE)
            self.re_HeroCards = re.compile(
                r"Dealt to %(PLYR)s \[\s*(?P<NEWCARDS>.+)\s*\]" % subst,
                re.MULTILINE)
            self.re_Action = re.compile(u"""
                %(PLYR)s\s+(?P<ATYPE>bets|checks|raises|completes|bring-ins|calls|folds|is\sall-In|double\sbets)
                (?:\s+[%(BRAX)s]?\s?%(CUR_SYM)s?(?P<BET>[.,\d]+)\s*(%(CUR)s)?\s?[%(BRAX)s]?)?
                \.?\s*$""" %  subst, re.MULTILINE|re.VERBOSE)
            self.re_ShownCards = re.compile(
                r"%s (?P<SHOWED>(?:doesn\'t )?shows?) "  %  player_re +
                r"\[ *(?P<CARDS>.+) *\](?P<COMBINATION>.+)\.",
                re.MULTILINE)
            self.re_CollectPot = re.compile(
                r"""%(PLYR)s\s+wins\s+(Lo\s\()?%(CUR_SYM)s?(?P<POT>[.,\d]+)\s*(%(CUR)s)?\)?""" %  subst,
                re.MULTILINE|re.VERBOSE)

    def readSupportedGames(self):
        return [["ring", "hold", "nl"],
                ["ring", "hold", "pl"],
                ["ring", "hold", "fl"],

                ["ring", "stud", "fl"],

                ["tour", "hold", "nl"],
                ["tour", "hold", "pl"],
                ["tour", "hold", "fl"],
                
                ["tour", "stud", "fl"],
               ]

    def determineGameType(self, handText):
        handText = handText.replace(u'\x00', u'')
        info = {}
        m = self.re_GameInfo.search(handText)
        if not m:
            m = self.re_GameInfoTrny.search(handText)
        if not m:
            m = self.re_Disconnected.search(handText)
            if m:
                message = _("Player Disconnected")
                raise FpdbHandPartial("Partial hand history: %s" % message)
            m = self.re_Cancelled.search(handText)
            if m:
                message = _("Table Closed")
                raise FpdbHandPartial("Partial hand history: %s" % message)
            m = self.re_GameStartLine.match(handText)
            if m and len(handText)<50:
                message = _("Game start line")
                raise FpdbHandPartial("Partial hand history: %s" % message)
            m = self.re_PreliminaryHand.search(handText)
            if m:
                message = _("Preliminary hand")
                raise FpdbHandPartial("Partial hand history: %s" % message)
            tmp = handText[0:200]
            log.error(_("PartyPokerToFpdb.determineGameType: '%s'") % tmp)
            raise FpdbParseError

        mg = m.groupdict()
        #print "DEBUG: mg: %s" % mg

        if 'LIMIT' in mg and mg['LIMIT'] != None:
            info['limitType'] = self.limits[mg['LIMIT']]
        if 'LIMIT2' in mg and mg['LIMIT2'] != None:
            info['limitType'] = self.limits[mg['LIMIT2']]
        if 'LIMIT3' in mg and mg['LIMIT3'] != None:
            info['limitType'] = self.limits[mg['LIMIT3']]
        if mg['LIMIT'] == None and mg['LIMIT2'] == None and mg['LIMIT3'] == None:
            info['limitType'] = 'fl'
        if 'GAME' in mg:
            (info['base'], info['category']) = self.games[mg['GAME']]
        if 'CASHBI' in mg and mg['CASHBI'] != None:
            # The summary is using buyin rather then listing the blinds
            # Only with NL games?
            mg['CASHBI'] = self.clearMoneyString(mg['CASHBI'])
            m_20BBmin = self.re_20BBmin.search(handText)
            if m_20BBmin is not None:
                try:
                    info['sb'] = self.NLim_Blinds_20bb[mg['CASHBI']][0]
                    info['bb'] = self.NLim_Blinds_20bb[mg['CASHBI']][1]
                except KeyError:
                    tmp = handText[0:200]
                    log.error(_("PartyPokerToFpdb.determineGameType: NLim_Blinds_20bb has no lookup for '%s' - '%s'") % (mg['CASHBI'], tmp))
                    raise FpdbParseError
            else:
                try:
                    nl_bb = str((Decimal(mg['CASHBI'])/50).quantize(Decimal("0.01")))
                    info['sb'] = self.Lim_Blinds[nl_bb][0]
                    info['bb'] = self.Lim_Blinds[nl_bb][1]
                except KeyError:
                    tmp = handText[0:200]
                    log.error(_("PartyPokerToFpdb.determineGameType: Lim_Blinds has no lookup for '%s' - '%s'") % (nl_bb, tmp))
                    raise FpdbParseError
        else:
            m = self.re_NewLevel.search(handText)
            if m:
                mg['SB'] = m.group('SB')
                mg['BB'] = m.group('BB')
            mg['SB'] = self.clearMoneyString(mg['SB'])
            mg['BB'] = self.clearMoneyString(mg['BB'])
            if 'SB' in mg:
                info['sb'] = mg['SB']
            if 'BB' in mg:
                info['bb'] = mg['BB']
        if 'CURRENCY' in mg:
            if mg['CURRENCY'] == None:
                info['currency'] = self.currencies['$']
            else:
                info['currency'] = self.currencies[mg['CURRENCY']]
        if 'MIXED' in mg:
            if mg['MIXED'] is not None: info['mix'] = self.mixes[mg['MIXED']]

        if 'TOURNO' in mg and mg['TOURNO'] is None:
            info['type'] = 'ring'
        else:
            info['type'] = 'tour'
            info['currency'] = "T$"

        if info['limitType'] == 'fl' and info['bb'] is not None:
            if info['type'] == 'ring':
                try:
                    info['sb'] = self.Lim_Blinds[mg['BB']][0]
                    info['bb'] = self.Lim_Blinds[mg['BB']][1]
                except KeyError:
                    tmp = handText[0:200]
                    log.error(_("PartyPokerToFpdb.determineGameType: Lim_Blinds has no lookup for '%s' - '%s'") % (mg['BB'], tmp))
                    raise FpdbParseError
            else:
                info['sb'] = str((Decimal(mg['SB'])/2).quantize(Decimal("0.01")))
                info['bb'] = str(Decimal(mg['SB']).quantize(Decimal("0.01")))
        #print "DEUBG: DGT.info: %s" % info
        return info


    def readHandInfo(self, hand):
        info, m2 = {}, None
        hand.handText = hand.handText.replace(u'\x00', u'')
        m  = self.re_HandInfo.search(hand.handText,re.DOTALL)
        if hand.gametype['type'] == 'ring':
            m2 = self.re_GameInfo.search(hand.handText)
        else:
            m2 = self.re_GameInfoTrny.search(hand.handText)
        if m is None or m2 is None:
            tmp = hand.handText[0:200]
            log.error(_("PartyPokerToFpdb.readHandInfo: '%s'") % tmp)
            raise FpdbParseError
        info.update(m.groupdict())
        info.update(m2.groupdict())

        for key in info:
            pass
            if key == 'DATETIME':
                #Saturday, July 25, 07:53:52 EDT 2009
                #Thursday, July 30, 21:40:41 MSKS 2009
                #Sunday, October 25, 13:39:07 MSK 2009
                #Mon Jul 12 13:38:32 EDT 2010
                timezone = "ET"
                m2 = re.search(
                    r"\w+?,?\s*?(?P<M>\w+)\s+(?P<D>\d+),?\s+(?P<H>\d+):(?P<MIN>\d+):(?P<S>\d+)\s+(?P<TZ>[A-Z]+)\s+(?P<Y>\d+)", 
                    info[key], 
                    re.UNICODE
                )
                if m2.group('TZ'):
                    timezone = m2.group('TZ')
                month = self.months[m2.group('M')]
                datetimestr = "%s/%s/%s %s:%s:%s" % (m2.group('Y'), month,m2.group('D'),m2.group('H'),m2.group('MIN'),m2.group('S'))
                hand.startTime = datetime.datetime.strptime(datetimestr, "%Y/%m/%d %H:%M:%S")
                hand.startTime = HandHistoryConverter.changeTimezone(hand.startTime, timezone, "UTC")
                # FIXME: some timezone correction required
                #tzShift = defaultdict(lambda:0, {'EDT': -5, 'EST': -6, 'MSKS': 3})
                #hand.starttime -= datetime.timedelta(hours=tzShift[m2.group('TZ')])

            if key == 'HID':
                hand.handid = info[key]
            if key == 'TABLE':
                if 'TOURNO' in info and info['TOURNO'] is None:
                    if info['TABLENO'] is not None:
                         hand.tablename = info[key] + ' ' + info['TABLENO']
                    else:
                        hand.tablename = info[key]
                else:
                    hand.tablename = info['TABLENO']
            if key == 'BUTTON':
                hand.buttonpos = info[key]
            if key == 'TOURNO':
                hand.tourNo = info[key]
            if key == 'TABLE_ID_WRAPPER':
                if info[key] == '#':
                    # FIXME: there is no such property in Hand class
                    self.isSNG = True
            if key == 'BUYIN':
                if info[key] == None:
                    # Freeroll tourney
                    hand.buyin = 0
                    hand.fee = 0
                    hand.buyinCurrency = "FREE"
                    hand.isKO = False
                elif hand.tourNo != None:
                    hand.buyin = 0
                    hand.fee = 0
                    hand.buyinCurrency = "FREE"
                    hand.isKO = False
                    if info[key].find("$")!=-1:
                        hand.buyinCurrency="USD"
                    elif info[key].find(u"€")!=-1:
                        hand.buyinCurrency="EUR"
                    else:
                        log.error(_("PartyPokerToFpdb.readHandInfo: Failed to detect currency Hand ID: '%s' - '%s'") % (hand.handid, info[key]))
                        raise FpdbParseError
                    info[key] = self.clearMoneyString(info[key].strip(u'$€'))
                    hand.buyin = int(100*Decimal(info[key]))
            if key == 'LEVEL':
                hand.level = info[key]
            if key == 'PLAY' and info['PLAY'] != 'Real':
                # if realy party doesn's save play money hh
                hand.gametype['currency'] = 'play'
            if key == 'MAX' and info[key] is not None:
                hand.maxseats = int(info[key])
        
        enetStart = datetime.datetime.strptime('20120101000000','%Y%m%d%H%M%S')
        enetStart = HandHistoryConverter.changeTimezone(enetStart, "ET", "UTC")    
        if hand.startTime > enetStart and len(hand.handid)<10:
            message = _("Converted Enet Hand")
            raise FpdbHandPartial("Partial hand history: %s" % message)


    def readButton(self, hand):
        m = self.re_Button.search(hand.handText)
        if m:
            hand.buttonpos = int(m.group('BUTTON'))
        else:
            log.info('readButton: ' + _('not found'))

    def readPlayerStacks(self, hand):
        log.debug("readPlayerStacks")
        m = self.re_PlayerInfo.finditer(hand.handText)
        maxKnownStack = 0
        zeroStackPlayers = []
        for a in m:
            if a.group('CASH') > '0':
                #record max known stack for use with players with unknown stack
                maxKnownStack = max(a.group('CASH'),maxKnownStack)
                hand.addPlayer(int(a.group('SEAT')), a.group('PNAME'), self.clearMoneyString(a.group('CASH')))
            else:
                #zero stacked players are added later
                zeroStackPlayers.append([int(a.group('SEAT')), a.group('PNAME'), self.clearMoneyString(a.group('CASH'))])
        if hand.gametype['type'] == 'ring':
            #finds first vacant seat after an exact seat
            def findFirstEmptySeat(startSeat):
                i=0
                while startSeat in occupiedSeats:
                    if (startSeat >= hand.maxseats and hand.maxseats!=None) or len(occupiedSeats)>=hand.maxseats:
                        startSeat = 0
                    startSeat += 1
                    i+=1
                    if i>10: break
                return startSeat
            
            re_SplitTest = re.compile(r"(joined the table|left the table|is sitting out)")
            re_JoiningPlayers = re.compile(r"(?P<PLAYERNAME>.+?) has joined the table")
            re_BBPostingPlayers = re.compile(r"(?P<PLAYERNAME>.+?) posts big blind", re.MULTILINE)
            re_LeavingPlayers = re.compile(r"(?P<PLAYERNAME>.+?) has left the table")

            match_JoiningPlayers = re_JoiningPlayers.findall(hand.handText)
            match_LeavingPlayers = re_LeavingPlayers.findall(hand.handText)
            match_BBPostingPlayers = []
            m = re_BBPostingPlayers.finditer(re_SplitTest.split(hand.handText)[-1])
            for player in m:
                match_BBPostingPlayers.append(player.group('PLAYERNAME'))

            #add every player with zero stack, but:
            #if a zero stacked player is just joined the table in this very hand then set his stack to maxKnownStack
            for p in zeroStackPlayers:
                if p[1] in match_JoiningPlayers:
                    p[2] = self.clearMoneyString(maxKnownStack)
                if not p[1] in match_LeavingPlayers:
                    hand.addPlayer(p[0],p[1],p[2])

            seatedPlayers = list([(f[1]) for f in hand.players])

            #it works for all known cases as of 2010-09-28
            #should be refined with using match_ActivePlayers instead of match_BBPostingPlayers
            #as a leaving and rejoining player could be active without posting a BB (sample HH needed)
            unseatedActivePlayers = list(set(match_BBPostingPlayers) - set(seatedPlayers))

            if unseatedActivePlayers:
                for player in unseatedActivePlayers:
                    occupiedSeats = list([(f[0]) for f in hand.players])
                    occupiedSeats.sort()
                    #previousBBPoster = match_BBPostingPlayers[match_BBPostingPlayers.index(player)-1]
                    #previousBBPosterSeat = dict([(f[1], f[0]) for f in hand.players])[previousBBPoster]
                    #newPlayerSeat = findFirstEmptySeat(previousBBPosterSeat)
                    # The commented out code above is 'correct' unless the unseated player is the only BB
                    # I'm willing to live with the unseated player being placed in the lowest seat for now.
                    newPlayerSeat = findFirstEmptySeat(1)
                    hand.addPlayer(newPlayerSeat,player,self.clearMoneyString(maxKnownStack))

    def markStreets(self, hand):
        if hand.gametype['base'] in ("hold"):
            m =  re.search(r"\*{2} Dealing down cards \*{2}"
                           r"(?P<PREFLOP>.+?)"
                           r"(?:\*{2} Dealing Flop \*{2} (?P<FLOP>\[ \S\S, \S\S, \S\S \].+?))?"
                           r"(?:\*{2} Dealing Turn \*{2} (?P<TURN>\[ \S\S \].+?))?"
                           r"(?:\*{2} Dealing River \*{2} (?P<RIVER>\[ \S\S \].+?))?$"
                            , hand.handText,re.DOTALL)
        elif hand.gametype['base'] in ("stud"):
            m =  re.search(
                r"(?P<ANTES>.+(?=\*\* Dealing \*\*)|.+)"
                r"(\*\* Dealing \*\*(?P<THIRD>.+(?=\*\* Dealing Fourth street \*\*)|.+))?"
                r"(\*\* Dealing Fourth street \*\*(?P<FOURTH>.+(?=\*\* Dealing Fifth street \*\*)|.+))?"
                r"(\*\* Dealing Fifth street \*\*(?P<FIFTH>.+(?=\*\* Dealing Sixth street \*\*)|.+))?"
                r"(\*\* Dealing Sixth street \*\*(?P<SIXTH>.+(?=\*\* Dealing River \*\*)|.+))?"
                r"(\*\* Dealing River \*\*(?P<SEVENTH>.+))?"
                 , hand.handText,re.DOTALL)

        hand.addStreets(m)

    def readCommunityCards(self, hand, street):
        if street in ('FLOP','TURN','RIVER'):
            m = self.re_Board.search(hand.streets[street])
            hand.setCommunityCards(street, renderCards(m.group('CARDS')))

    def readAntes(self, hand):
        log.debug("reading antes")
        m = self.re_Antes.finditer(hand.handText)
        for player in m:
            hand.addAnte(player.group('PNAME'), self.clearMoneyString(player.group('ANTE')))

    def readBlinds(self, hand):
        noSmallBlind = bool(self.re_NoSmallBlind.search(hand.handText))
        if hand.gametype['type'] == 'ring':
            try:
                assert noSmallBlind==False
                for m in self.re_PostSB.finditer(hand.handText):
                    hand.addBlind(m.group('PNAME'), 'small blind', self.clearMoneyString(m.group('SB')))
            except: # no small blind
                hand.addBlind(None, None, None)

            for a in self.re_PostBB.finditer(hand.handText):
                hand.addBlind(a.group('PNAME'), 'big blind', self.clearMoneyString(a.group('BB')))

            for a in self.re_PostDead.finditer(hand.handText):
                hand.addBlind(a.group('PNAME'), 'both', self.clearMoneyString(a.group('BBNDEAD')))
        else:
            # party doesn't track blinds for tournaments
            # so there're some cra^Wcaclulations
            if hand.buttonpos == 0:
                self.readButton(hand)
            # NOTE: code below depends on Hand's implementation
            # playersMap - dict {seat: (pname,stack)}
            playersMap = dict([(f[0], f[1:3]) for f in hand.players if f[1] in hand.handText.split('Trny:')[-1]])
            maxSeat = max(playersMap)

            def findFirstNonEmptySeat(startSeat):
                while startSeat not in playersMap:
                    if startSeat >= maxSeat:
                        startSeat = 0
                    startSeat += 1
                return startSeat
            smartMin = lambda A,B: A if float(A) <= float(B) else B

            if noSmallBlind:
                hand.addBlind(None, None, None)
                smallBlindSeat = int(hand.buttonpos)
            else:
                if len(hand.players)==2:
                    smallBlindSeat = int(hand.buttonpos)
                else:
                    smallBlindSeat = findFirstNonEmptySeat(int(hand.buttonpos) + 1)
                blind = smartMin(hand.sb, playersMap[smallBlindSeat][1])
                hand.addBlind(playersMap[smallBlindSeat][0], 'small blind', blind)

            bigBlindSeat = findFirstNonEmptySeat(smallBlindSeat + 1)
            blind = smartMin(hand.bb, playersMap[bigBlindSeat][1])
            hand.addBlind(playersMap[bigBlindSeat][0], 'big blind', blind)

    def readBringIn(self, hand):
        pass
        #m = self.re_BringIn.search(hand.handText,re.DOTALL)
        #if m:
        #    #~ logging.debug("readBringIn: %s for %s" %(m.group('PNAME'),  m.group('BRINGIN')))
        #    hand.addBringIn(m.group('PNAME'),  m.group('BRINGIN'))

    def readHeroCards(self, hand):
        # we need to grab hero's cards
        for street in ('PREFLOP',):
            if street in hand.streets.keys():
                m = self.re_HeroCards.finditer(hand.streets[street])
                for found in m:
                    hand.hero = found.group('PNAME')
                    newcards = renderCards(found.group('NEWCARDS'))
                    hand.addHoleCards(street, hand.hero, closed=newcards, shown=False, mucked=False, dealt=True)
                    
        for street, text in hand.streets.iteritems():
            if not text or street in ('PREFLOP', 'DEAL'): continue  # already done these
            m = self.re_HeroCards.finditer(hand.streets[street])
            for found in m:
                player = found.group('PNAME')
                if street != 'SEVENTH':
                    newcards = renderCards(found.group('NEWCARDS'))
                    oldcards = []
                else:
                    oldcards = renderCards(found.group('NEWCARDS'))
                    newcards = []

                if street == 'THIRD' and len(newcards) == 3: # hero in stud game
                    hand.hero = player
                    hand.dealt.add(player) # need this for stud??
                    hand.addHoleCards(street, player, closed=newcards[0:2], open=[newcards[2]], shown=False, mucked=False, dealt=False)
                else:
                    hand.addHoleCards(street, player, open=newcards, closed=oldcards, shown=False, mucked=False, dealt=False)
                    
    def readAction(self, hand, street):
        m = self.re_Action.finditer(hand.streets[street])
        for action in m:
            acts = action.groupdict()
            #print "DEBUG: acts: %s" % acts
            playerName = action.group('PNAME')
            amount = self.clearMoneyString(action.group('BET')) if action.group('BET') else None
            actionType = action.group('ATYPE')

            if actionType == 'folds':
                hand.addFold( street, playerName )
            elif actionType == 'checks':
                hand.addCheck( street, playerName )
            elif actionType == 'calls':
                hand.addCall( street, playerName, amount )
            elif actionType == 'raises':
                if street == 'PREFLOP' and \
                    playerName in [item[0] for item in hand.actions['BLINDSANTES'] if item[2]!='ante']:
                    # preflop raise from blind
                    hand.addCallandRaise( street, playerName, amount )
                else:
                    hand.addCallandRaise( street, playerName, amount )
            elif actionType == 'bets' or actionType ==  'double bets':
                hand.addBet( street, playerName, amount )
            elif actionType == 'completes':
                hand.addComplete( street, playerName, amount )
            elif actionType == 'bring-ins':
                hand.addBringIn( playerName, amount)
            elif actionType == 'is all-In':
                hand.addAllIn(street, playerName, amount)
            else:
                log.error((_("PartyPokerToFpdb: Unimplemented %s: '%s' '%s'") + " hid:%s") % ("readAction", playerName, actionType, hand.handid))
                raise FpdbParseError

    def readShowdownActions(self, hand):
        # all action in readShownCards
        pass

    def readCollectPot(self,hand):
        hand.setUncalledBets(True)
        for m in self.re_CollectPot.finditer(hand.handText):
            hand.addCollectPot(player=m.group('PNAME'),pot=self.clearMoneyString(m.group('POT')))

    def readShownCards(self,hand):
        for m in self.re_ShownCards.finditer(hand.handText):
            if m.group('CARDS') is not None:
                cards = renderCards(m.group('CARDS'))

                mucked = m.group('SHOWED') != "show"

                hand.addShownCards(cards=cards, player=m.group('PNAME'), shown=True, mucked=mucked, string=m.group('COMBINATION'))

    @staticmethod
    def getTableTitleRe(type, table_name=None, tournament = None, table_number=None):
        "Returns string to search in windows titles"
        if type=="tour":
            if table_name:
                TableName = table_name.split(" ")
                print 'party', 'getTableTitleRe', "%s.+Table\s#%s" % (TableName[0], table_number)
                if len(TableName[1]) > 6:
                    return "#%s" % (table_number)
                else:
                   return "%s.+Table\s#%s" % (TableName[0], table_number)
            else:
                #
                #sng's seem to get passed in with:
                #   table_name = None
                #   tournament=8-digit tourney number
                #   table_number = 7 digit table number
                # screen string is normally Turbo|Speed|(etc) #table_number
                #
                return "#%s" % (table_number)
        else:
            return table_name

def renderCards(string):
    "Splits strings like ' Js, 4d '"
    cards = string.strip().split(' ')
    return filter(len, map(lambda x: x.strip(' ,'), cards))
