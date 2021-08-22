#!/usr/bin/python3
# Copyright C Devereaux 2016-2018,2021

# An adaptation of my "broken needle" algorithm, to be used when regexp are to be avoided
# like with an unsanitized input, along with a few different approaches to exploit the output.

# verbosity of the output, to help with debugging
debug = 0

# 1 mostly shows the tests done
# 2 display basic output, mostly for subsetting diagnostics
# 3 is very verbose about everything

# The needles to be found, and replaced by a geographical code
needlesgeo= {
    'TOTALLY NOT THERE': '00',  # not present in the haystack, LOL
    'NEW ORLEANS': '01',        # NOLA, Mardi Gras city
    'ORLEANS': '02',            # the european city
    'NEW YORK': '03',           # the state
    'NEW YORK CITY': '04',      # the city that never sleeps
    'YORKTOWN': '05',           # in Virginia, which had a famous civil war battle in 1781
    'NEW YORKTOWN': '06',       # a city that should exist?
    'YORK': '07',               # in England
    'WALES': '08',              # the country next to England, part of the UK
    'SOUTH WALES': '09',        # De Cymru, the loosely defined region of Wales bordered by England to the east and mid Wales to the nort
    'NEW SOUTH WALES': '10',    # in Australia, where the city Syndey is
    'SYDNEY': '11',             # Yes, this city
    'AUSTRALIA': '12',          # Yes, in this country
    'AUSTRIA': '13',            # No, not this one, and why Levenstein would be of limited help
    '*': '55',                  # Some unsanitized thing that could cause issues with regex
    'N*': '66',                 # Another
    'A': '77',                  # "A" typo actually
    'YO': '88',                 # Because YOLO! (and matches York)
    'NEW': '99'                 # A wild match
}

# The vanilla input
haystackgeo1="NEW ORLEANS,ORLEANS,NEW YORK,NEW YORK CITY,YORKTOWN,NEW YORKTOWN,YORK,WALES,SOUTH WALES,NEW SOUTH WALES,SYDNEY,AUSTRALIA,AUSTRIA"
# Oops, all spaces became commas
haystackgeo2="NEW,ORLEANS,ORLEANS,NEW,YORK,NEW,YORK,CITY,YORKTOWN,NEW,YORKTOWN,YORK,WALES,SOUTH,WALES,NEW,SOUTH,WALES,SYDNEY,AUSTRALIA,AUSTRIA"
# Oops, now it has also become almost fully quoted: the hay is "','"
# even worse, it's littered with various amounts of periods ".", exclamations "!", stars "*" and tildes "~" that break the sequence here and there
haystackgeo3="'NEW','ORLEANS...ORLEANS','NEW','YORK','NEW','YORK!!!!CITY','YORKTOWN','NEW*YORKTOWN','YORK!!!!WALES','SOUTH~~~WALES','NEW','SOUTH~WALES','SYDNEY','AUSTRALIA','AUSTRIA'"


# Let's try to fully recover the sequences

# tolerance factor for broken needle distance between pieces:
# <= 4 to allow the 3 chars of ','
piecedistancetolerance = 4

# size requirement for a broken needle piece to be used in the matching:
# >1 to exclude standalone chars that would create too many alternatives
piecesizerequirement = 1


# flatten an array of array into an array: cool version with iterator
def _flatten_generator(iterable):
    try:
        iterator = iter(iterable)
    except TypeError:
        yield iterable
    else:
        for element in iterator:
            yield from flatten1(element)


def flatten1(iterable):
    if isinstance(iterable, str):
        return [iterable]
    else:
        return list(_flatten_generator(iterable))


# but this is far easier to understand and maintain, while
# the goal is not to do fancy code using every feature python
# supports, but write code that most people can tweak and improve
def flatten2(input_array):
    if isinstance(input_array, str):
        return [input_array]
    else:
        result_array = []
        for element in input_array:
            if isinstance(element, int):
                result_array.append(element)
            elif isinstance(element, str):
                result_array.append(element)
            elif isinstance(element, list):
                result_array += flatten2(element)
        return result_array


# main algorithm: the "broken needle": generalizes and expands a regex solution:
# for a set of candidate needles (signal), and a haystack (signal + noise)
# returns both the array of matches (for each needle: start,length,stop)
# and the list of possibles (for each haystack position: the valid needles)
# without cleaning the haystack, without inferring anything about the haystack
# or the corruption that has happened to the haystack

# The broken needle break the needle into pieces (ex: NEW ORLEANS => NEW and ORLEANS)
# then looks for the ordered sequence of pieces in the 1d haystack
# to allow for hay between the pieces (ex: spaces replaced by some commas)
# with a configurable tolerance of how far apart the pieces can be (X=3=,,,)
# while considering alternatives matches (ORLEANS does match NEW ORLEANS)
# and keeping them at the beginning: these subsettings (overlapping) needles
# are removed during further processing.
#
# It doesn't do the opposite (splitting the haystack then comparing the needles)
# because the acceptable splits of the haystack are unknown, because it was
# corrupted in an unknown way, while the needles are intact and can be split
# to any degree we want: this will work as long as the pieces are all present,
# and in the right sequence (the pieces must not have been shuffled)
#
# Even if we assume here the damage mostly affect the word separators (spaces)
# and the list separators (commas), the solution is flexible and extensible:
# to account for corruption in the individual letters (YORK=> YQRK), the
# needle finder could use a fuzzy find (ex: Levenstein distance...) ; the
# good thing is that it is not REQUIRED, so it doesn't introduce new problems
# like confusing AUSTRIA and AUSTRALIA.
#
# For the resulting problem of a needle subsetting another, we do not simply
# return the various possible needles: we also build an array of the haystack
# with each alternative per position: it can be later parsed to pick any
# combination of needles minimizing hay / maximizing needle content, or any
# other custom metric, to complement more algorithmically complex approaches
# and naive approaches ("ORLEANS orphenates NEW so pick the needle NEW ORLEANS
# instead of just ORLEANS for the haystack NEW ORLEANS")

# WONTFIX: could memoize by building a dict of broken needle positions
# However, complicated and memory intensive, while the dictionaries are small
# so not necessarily faster (+ premature optimization is the root of all evil)

def brokenneedlealgorithm(needles, haystack):
    # returns:
    found = {}  # dict of arrays: which broken needles were found:
    # at which starting positions, for how long, at which ending position
    # the ending position is required as the hay may impact calculation for subsetting needles
    alternatives = [None] * len(haystack)  # alternative needles per position: initially empty

    # first, filter the needles based on a size requirement:
    # useful if, for example, one-character pieces or ASCII punctuation should be removed

    # save the previous needle to break the loop, as alternatives may cause us to keep trying
    previousneedle = None
    # loop on each needle, then on each of its pieces trying to find a full set of pieces
    for needle in needles.keys():
        if debug > 1:
            print("Needle = " + str(needle))
        piecesfound = {}  # dict: for every piece of a needle, where in starts, how long, stops
        # WONTFIX: for a needle, how long is different from needle stop position due to hay
        # this is not the case for a piece of a needle: startpos+howlong=stoppos, fully redundant
        # however, we keep the end position there for consistency
        needlestartpos = None  # where the needle begins (ie beginning of the first piece)
        needlestoppos = None  # where the needle ends (ie end of the last piece)
        # truly known when we have all the pieces, then flushed, so we keep separately what was the former one
        # so that we can detect when we are done parsing while also allowing for retries
        # meaning we can't easily use a for loop, but have to use a while loop instead
        previousneedlestoppos = None

        # break the needle on the known separator that is lost/damaged in the haystack
        # WONTFIX: the needle could be broken further if spaces are not the only issue
        # eg if the ASCII chars like -/({[ etc are also damaged, only keep a-zA-Z0-9
        brokenneedle = str.split(needle, " ")

        # filter with an list comprehension, which may be too fancy?
        # TODO: another reason to consider doing a separate fonction: things like
        # len(brokenneedle)>piecesizerequirement etc. could be beneficial
        brokenneedle = [x for x in brokenneedle if len(x) > piecesizerequirement]

        # due to the above, there could be nothing left due to the filter, so tell us about that
        if len(brokenneedle) < 1:
            if debug > 1:
                print("Not checking for the fully filtered needle: " + str(needle))
            else:
                # if the array is not empty (which case would be skipped at the while), tell us:
                if brokenneedle:
                    print("Currently checking for this needle, broken into size-filtered pieces:")
                    print(brokenneedle)

        # we may give up early, like if we wont have all the needle pieces in order
        # or we may try again after success, if all the pieces suggest one or more subset
        tryfindingbrokenneedle = True
        tryagainwhere = 0

        p = 0  # current piece number being handled for a given needle
        piecestartpos = None  # position in the haystack where the piece begins
        piecestoppos = None  # position in the haystack where the piece ends

        # this is not a for loop but a while, to allow for extra things like retrying
        while tryfindingbrokenneedle is True and brokenneedle:
            if tryagainwhere:
                if debug>1:
                    print ("tryagainwhere=" + str(tryagainwhere))
                if debug>2:
                    print ("visible haystack from there:")
                    print (str(haystack)[tryagainwhere:])
            # stop if we are on the last needle without retrying again further
            if previousneedle == needle:
                if not tryagainwhere > 0:
                    break
            # attention: you can do off by one between brokenneedle and p
            if debug > 1:
                print(str("when broken, length of needle=") + str(len(brokenneedle)))
            for piece in brokenneedle:
                if tryagainwhere > 0:
                    # All the comparisons are case insensitive ; the simplest way to do that
                    # is to compare both after converting each to lowercase!
                    # Also, in case the needle case matters (ex: CamelCase), this restores it into the haystack
                    if p ==0:
                        piecestartpos = haystack.lower().find(piece.lower(), tryagainwhere)
                    else:
                        # tryagainwhere should not replace where the previous piece was found
                        # it's just a floor, if the previous piece is above it, use it:
                        previouspiecestartpos=piecesfound[p-1][0]
                        piecestartpos = haystack.lower().find(piece.lower(), max(previouspiecestartpos,tryagainwhere))
                else:
                    if p==0:
                        piecestartpos = haystack.lower().find(piece.lower())
                    else:
                        previouspiecestartpos = piecesfound[p-1][0]
                        piecestartpos = haystack.lower().find(piece.lower(), previouspiecestartpos)

                # later also taken as the tempory end of the needle, until we have found all of its pieces
                piecestoppos = piecestartpos + len(piece) - 1

                piecetolerance = False  # by default, fail the pieces found unless the tolerance is met
                # this is used at the moment for the following conditions:
                # 1) a single missing piece immediately disqualifies the potential needle
                #
                # DEPRECATED:2) we are discovering again the beginning of a needle found before at this exact position (!!!)
                # This 2nd condition should NO LONGER be necessary given the algorithm logic
                # however it *WAS* happening until the code was extended to handle several edgecases
                # so it is kept as a reminder
                #
                # 3) the piece is ordered within tolerance, taken as meaning 2 separate things:
                # 3a) basic: while taking tolerance into account, the pieces are not too far apart from each other
                # 3b) better: if more than one piece, they are all in order (NEW YORK is ok, YORK NEW is not!)

                if p == 0:
                    # the beginning of the first ever piece (p=0) of a needle
                    # defines where this needle itself starts at (was: None)
                    needlestartpos = piecestartpos

                # this is condition 1)
                if piecestartpos == -1:
                    tryfindingbrokenneedle = False
                    break  # if not found: break out of for.piece to resume the for.needle
                else:
                    # show what we have for now
                    if debug > 2:
                        print("all needles found currently:" + str(found))
                        print("for needle: " + needle + " @ piece:" + piece)
                        print("all pieces found currently:" + str(piecesfound))
                        print("a piece was just found @ " + str(piecestartpos) + "-" + str(piecestoppos))

                    # this is condition 2) as it shouldn't happen anymore, now is an assert
                    # to cause a bug and force a reinspection of this code
                    try:
                        alreadyknownneedles = found[piece]
                    except KeyError:
                        alreadyknownneedles = []
                        pass
                    assert (needlestartpos not in alreadyknownneedles)

                    # this is condition 3: pieces are in order
                    if p == 0:
                        # automatically passed for more than one piece
                        piecetolerance = True
                    if p > 0:
                        # Condition 3a:  making sure the pieces are not too far apart
                        # meaning the end of a previous piece + tolerance must be >= start of a new piece
                        # item 0 is the start, item 1 is the len
                        if debug > 2:
                            print(str(piecesfound[p-1][0]) + "+" + str(piecesfound[p-1][1]) + "+" + str(piecedistancetolerance) + "?>=" + str(piecestartpos))
                        if not piecesfound[p-1][0] + piecesfound[p-1][1] +int(piecedistancetolerance) >= piecestartpos:
                            if debug >2:
                                print("new piece distance checks breaks tolerance, rejecting")
                        else:
                            # Condition 3b: if all the known pieces are in order
                            orderfound = []
                            for pp in piecesfound:
                                orderfound.append(piecesfound[pp][0])
                            # then the new one
                            orderfound.append(piecestartpos)
                            if not sorted(orderfound) == orderfound:
                                if debug>2:
                                    print("we would break the logical order if adding, so rejecting " + str(piece))
                                piecetolerance = False
                            else:
                                piecetolerance = True

                    # if the piece has passed all the requirements
                    if piecetolerance is True:
                        if debug > 2:
                            print("adding piece that passes all requirements :" + str(piece))
                            print("p=" + str(p) + ", @=" + str(piecestartpos) + ":" + str(piecestoppos))

                        # add to the dict of pieces where this one was found
                        piecesfound[p] = [piecestartpos, len(piece), piecestoppos]

                        if debug > 2:
                            print("piecesfound current:" + str(piecesfound))

                        # increment the piece counter
                        p = p + 1
                        # WARNING: this can cause an off by one error if p not decremented
                        # in the end, ie when we will have found all pieces
                    else:
                        if debug > 2:
                            print("rejecting piece for whatever condition fail:" + str(piece))

                        # if it fails the requirements, keep trying, but past the issue:
                        # tryagainwhere should not be 0 if some pieces were already found:
                        # can assemble where the good pieces where found, then guess where to restart past
                        # a simple guess is the max +1
                        pp=p-1
                        assemblewherepiecefound=[]
                        while pp > -1:
                            try:
                                assemblewherepiecefound.append(piecesfound[pp][0])
                            except IndexError:
                                pass
                            pp=pp-1
                        tryagainwhere = max(assemblewherepiecefound)
                        tryagainwhere = tryagainwhere + 1
                        if debug>2:
                            print("Choice of where to try again=" + str(tryagainwhere) + " given:" )
                            print(str(assemblewherepiecefound))
                        # then flush all these failing pieces
                        piecesfound={}
                        # restart from scratch
                        p=0
                        # and try again at this further spot by breaking on the for to go back to the while
                        break

            # when we indeed have found all of its pieces
            if len(piecesfound) == len(brokenneedle):
                # first, prevent the off-by-one on p
                p = p - 1
                # given this previous off-by-one bug, do some further sanity checks
                # like if the starting point is a number (!)
                if debug > 1:
                    print("last piece is p=" + str(p))
                if debug > 2:
                    print("needlestartpos=" + str(needlestartpos))
                    print("piecestartpos=" + str(piecestartpos))

                # sanity checks:
                assert isinstance(needlestartpos, int)
                assert isinstance(piecestartpos, int)
                # check if the starting point means something (!)
                assert needlestartpos >= 0
                assert needlestartpos <= piecestartpos

                # needlestartpos will be < last piece start position as min(len(piece))=1
                if debug>2:
                      print("needlestoppos=piecestoppos=" + str(piecestoppos))

                # check if the end point is plausible given the tolerance
                needlestoppos = piecestoppos

                # stricly inferior: no size 0 needle!
                assert needlestartpos<needlestoppos

                # TODO: there should be a more precise accounting of the hay
                #
                # until then, estimate to min(1,somehay times the number of pieces)
                somehay=2
                # this way it's never fully ignored
                if p==0:
                    psomehay=1
                else:
                    psomehay=p*somehay

                # Goal of this assertion: making sure we haven't included pieces that are too far apart
                # but more or less consecutive even when accounting for the hay
                # Alternatively, could also do psomehay < actualhay
                if debug > 2:
                    print("needle start at " + str(needlestartpos))
                    print("needle end at " + str(needlestoppos))
                    print("needle made of " + str(p) + " pieces with somehay=" + str(somehay))
                    print("min(1,p*somehay)=psomehay=" + str(psomehay))
                    print("logic test applied:")
                    print(str(needlestoppos) + " - " + str(needlestartpos) + " ?<= " + str(len(needle)) + " + p*somehay=" +  str(p*somehay))
                assert (needlestoppos-needlestartpos  <=  len(needle) + psomehay )

                # at this stage, we can assume a match so populate the solutions
                # first, check if this needle was already found elsewhere
                try:
                    # arg 0 is the needlestart
                    alreadyfound = flatten2(found[needle][0])
                except KeyError:
                    alreadyfound = None
                    pass

                # array of arrays, so the new needle itself is an array of strings, not ints, as a precaution
                newlyfoundneedle=[str(needlestartpos), str(len(needle)), str(needlestoppos)]

                if alreadyfound is None:
                    # making a dict of arrays
                    found[needle] = [ newlyfoundneedle ]
                    if debug > 2:
                        print("Newly found needle added")
                else:
                    if debug > 2:
                        print("Needle found in several position, indicating a subset issue requiring parsing alternatives")
                        print(alreadyfound)

                    # Should not happen at this point given prior tests, so assert that !
                    assert (needlestartpos not in alreadyfound)

                    # then add it to the dict of arrays
                    found[needle].append(newlyfoundneedle)

                    if debug > 2:
                        print("This needle know positions are now: ")
                        print(str(found[needle]))

                # also populate the alternatives by parsing the range and appending if needed
                cur = needlestartpos
                if debug > 1:
                    print("Populating alternatives from " + str(cur) + " to " + str(needlestoppos))
                while cur <= needlestoppos:
                    currentalt = alternatives[cur]
                    if currentalt is None:
                        alternatives[cur] = [needle]
                    else:
                        # there is already something else
                        ac = alternatives[cur]
                        acf = flatten1(ac)
                        if needle not in acf:
                            acf.append(needle)
                            alternatives[cur] = acf
                    cur = cur + 1
                    #  do not try to go beyond the end of line!
                    if cur == len(haystack):
                        # this is because on the very last match,
                        # needlestoppos could be at the end of the haystack
                        break

                # when we indeed have found all of the pieces and processed them,
                # we may then try again if there are more matches of the needle
                # broken pieces "right after" this needle (like for subsetting needles)
                # define "right after" as the end of this piece +1
                if debug > 1:
                    print("Do we want to try again past " + str(piecestoppos) + " where it was found?")
                nextpiecepos = 0
                nextpieceorder= []
                for nextpiece in brokenneedle:
                    nextpiecepos = haystack.lower().find(nextpiece.lower(), piecestoppos + 1)
                    # if there are all the pieces, worth trying again!
                    # But check if they are in order: sorted wont affect a strictly increasing list
                    nextpieceorder.append(nextpiecepos)
                    if not nextpieceorder==sorted(nextpieceorder):
                        if debug>1:
                            print("Next pieces are not ordered correctly")
                    if not (nextpiecepos > 0) or not nextpieceorder==sorted(nextpieceorder):
                        tryagainwhere = 0
                        tryfindingbrokenneedle = False
                        if debug > 1:
                            print("Will not try again because " + str(tryagainwhere) + " for " + needle + "@" + nextpiece)
                        break
                    else:
                        tryagainwhere = piecestoppos+1
                        if debug > 1:
                            print("Ready to try again past " + str(tryagainwhere) + " @ " + str( nextpiecepos) + " for " + needle + " @ " + nextpiece)

                # all done, flush needle positions to start anew
                # and also flush the pieces found when tryagainwhere
                if tryagainwhere > 0:
                    if debug > 1:
                        print("Now trying again after flushing")
                    piecesfound = {}
                    p = 0
                needlestartpos = None
                previousneedlestoppos = needlestoppos
                needlestoppos = None

            # since we are looping on tryagainwhere being true, it must be set to false
            # to stop when the last needle has been tried: do that by saving the current needle
            previousneedle = needle

    # In a separate function, we will refine the needles as the needles found
    # are subsetting, meaning NEW YORK and NEW YORK CITY will both match on "NEW YORK CITY"
    # The alternatives present that same information in a different way.

    # Various approaches will be possible; it would be faster to do that straight from here
    # However, it would be both less legible, and less flexible
    return found, alternatives


# The naive approach would be to go along the range, build a dict of matches
# for each position, then using the dict, checking for range conflict:
# in case of conflicting options, just decide which to keep by taking the longest
#
# But problem if due to subsetting needles, we have (assuming the separators away for clarity):
# 1 [0:10] : span 10
# 2 [11:13] : span 3
# 3 [14:17] : span 4
# 4 [18:23] : span 6
# 5 [2:15] : span 13
# 6 [4:16] : span 12
#
# The dict is built : at spot 0 (candidate 1 span 10) ... at position 2: candidate 5 span 15
# Then naive logic is applied : 15>10 so starting at position 2, would purge candidate 1 from the candidates

# input dict will be ordered:

from collections import OrderedDict

def naiverefineneedles(subsettingneedles):
    # shortest first
    odsn = OrderedDict(sorted(subsettingneedles.items(), key=lambda t: len(t[0])))
    # reversed: longest first
    odsnr = OrderedDict(sorted(subsettingneedles.items(), key=lambda t: len(t[0]), reverse=True))


    if debug > 1:
        print(odsn)

    for k in odsnr.keys():
        a = odsnr[k]
        for v in a:
            # v is an array of values: arg0 start, arg1 len, arg3 pos
            longstartpos = int(v[0])
            # cant just use startpos + len(k) as that would be forgetting some hay
            longstoppos = int(v[2])
            # if that span in present in the others, remove
            for kk in odsn.keys():
                # exception for self
                if kk == k:
                    if debug > 1:
                        print("skipping self:" + str(kk))
                else:
                    aa = odsn[kk]
                    for vv in aa:
                        shortstartpos = int(vv[0])
                        shortstoppos = int(vv[2])
                        # test for full overlap of the short by the long
                        if longstartpos <= shortstartpos and longstoppos >= shortstoppos:
                            if debug > 1:
                                print("keeping -> k=" + str(k) + "\t\t\tkk=" + str(kk) + " <- removing @ " +str(shortstartpos))
                                print(str(longstartpos) + "<=?" + str(shortstartpos))
                                print(str(longstoppos) + ">=?" + str(shortstoppos))
                            # delete this overlap: remove short
                            try:
                                offsets = subsettingneedles[kk]
                            except KeyError:
                                # WONTFIX: shouldn't happen anymore as the list is only emptied at the end
                                print ("ERROR on subsetting due to possibly empty offsets for " +str(kk))
                                offsets=None

                            if debug>2:
                                print ("\t\t\t\t\tWas : " + str(offsets))
                                print (str(vv[0]))

                            if offsets is not None:
                                # can easily filter with a list comprehension
                                # for an array
                                # offsetsclean= {o for o in offsets if o is not vv}
                                # but this is more readable

                                offsetsclean=[]
                                for o in offsets:
                                    if o[0] is not vv[0]:
                                        offsetsclean.append(o)

                                subsettingneedles[kk] = offsetsclean
                                if debug>2:
                                    print ("\t\t\t\t\tNow : " + str(offsetsclean))
                            # WONTFIX: removing the empty parts from subsettingneedles right
                            # here was not working correctly, and was causing the key errors

    # So instead, clean the list once done
    # An empty Set() was found with just "is not None"
    nosubsettingneedles = {k: v for k, v in subsettingneedles.items() if v is not None and len(v)!=0}

    return (nosubsettingneedles)


# This is wrong, we can see why graphically: 3 non overlapping matches are possible:

# @0123456789 : position
#  11111111112223333444444
#  --55555555555555-444444
#  ----6666666666666444444
#
# The needle 5 is longer than 1 or 2 or 3 individually, but less than the set 1+2+3
# so 1+2+3 should be selected, as it minimizes the amount of "hay"
#
# Ignoring the 3rd option at first, the known options are:
# @0: 1 (10)
# @1: 1 (10)
# @2: 1 (10), 5 (13) : naive approach would remove 1
# ...
# @11: 2 (3), 5 (13) : naive approach would remove 2
# ...
# @14: 3 (4), 5 (13) : naive approach would remove 3
# => PROBLEM!
#
# This problem can be fixed by recursively sorting the needles, or by building continuity.
#
# Building continuity is the easiest:
#  @0 : 1 ends on 10, look if there's anything starting at 10, 11, (etc within tolerance)
# Indeed there's another path as 2 starts right there, so we can build an extended span
# This is called doing a forward look: by repeating the forward look at the end of 2,
# the extended span will end up being 1+2+3+4=0:23 : using the sequence reaches to 23
# For each of the positions in this extended span, consider alternatives outside this set:
#  @0:nothing, @1:nothing @2: 5=2:15 then nothing
#
# So by looking forward  it's 5 that should be eliminated, not the others!
#
# Ideally, we could be looking forward then looking backward to extend both ways,
# which will cover both the prefixes and suffixes (YORK, NEW YORK and NEW YORK CITY
# and WALES, SOUTH WALES, NEW SOUTH WALES)



# Takes as an input needles and a haystack, computes the refined needles,
# then applies these to the haystack by doing a replace-in-position
# which does not depends on any regex and is thus less risky
# Returns the recovered haystack, and the encoded haystack
# where needles are replaced by their codes and an optional separator

def brokenneedleapply(dictin, haystackin, separator_start, separator_stop):

    needles, needlesalternatives = brokenneedlealgorithm(dictin, haystackin)
    needlesrefined = naiverefineneedles(needles)

    # initialize
    recovered=haystackin
    needlesrefinedcopy=needlesrefined

    # To keep track of needles already processed and not update their position, another dict
    # only useful for debug purposes to avoid displaying an offset update that won't be used
    needlesdone={}

    if debug>1:
        print("Needles refined:")
        print(needlesrefined)

    if debug>2:
        print("Needles:")
        print(needles)
        print("Needles alternatives:")
        print(needlesalternatives)

    for n in needlesrefined.keys():
        if debug>2:
            print("Needle is '" + str(n) + "'")

        # FIXME: We assume a needle can only be present once.
        # So fail, as this algorithm will need improvements to tolerate more offsets than one
        if len(needlesrefined[n]) !=1:
            print ("cardinality error on "  + str(n) + " found at " + str(needlesrefined[n]))
            exit(1)
        else:
            [[sstart, slen, sstop]] = needlesrefined[n]

        nstart=int(sstart)
        nlen=int(slen)
        nstop=int(sstop)

        # Applying the needle means replacing a piece of text by another.
        # It needs to take into account the size difference:
        # Doing even one replacement may change the offsets of all subsequent needles
        # So we compute the delta to alter them:
        delta = len(n) - 1 -nstop +nstart
        # We truncate to before, apply the string, truncate what's after, and glue it together
        replaced= recovered[:nstart] +  str(n) + recovered[nstop+1:]

        if debug>2:
            print ("Delta=" + str(delta) +": len(n)=" +str(len(n)) + " -1 -nstop=" +str(nstop) + "+nstart=" + str(nstart) + "\n")
            print("Gluing with delta=" +str(delta) + ":\n>" + str(recovered[:nstart]) + "<+>" + str(n) + "<+>" + str(recovered[nstop+1:]) +"\n")
            print('replaced=' +str(replaced))

        # For non zero delta, update the needles.
        # Making a for loop within another for loop is NOT EFFICIENT: O(n^2), quadratic!
        # HOWEVER it's easier to understand and maintain, and the performance loss may be acceptable
        # since the number of refined needles will be very limited
        if delta != 0:
            if debug>2:
                print("Tweaking needles position")
            for m in needlesrefined.keys():
                # this needlesdone is not really needed, except for debug purposes
                if not n == m and not m in needlesdone.keys():
                    [[tstart, tlen, tstop]] = needlesrefined[m]
                    mstart = int(tstart)
                    mlen = int(tlen)
                    mstop = int(tstop)
                    # For any other needle starting after the current one, update its offsets
                    #if mstart > nstop:
                    # But the stop of the needle can become less that nstop due to the delta!
                    #if (mstart > nstart + len(n)):
                    # HOWEVER, this doesn't matter: all that does is the start point!
                    if mstart>nstart:
                        if debug>2:
                            print('needle ' + str(m) + ' was:' + str(needlesrefined[m]))
                        mstartnew=mstart+delta
                        mstopnew=mstop+delta
                        mnew = [str(mstartnew), str(mlen),str(mstopnew)]
                        needlesrefined[m]=[mnew]
                        if debug>2:
                            print('needle ' + str(m) + ' now:' + str(needlesrefined[m]))
        # Apply the update for the next loop
        recovered=replaced
        # And mark the needle as processed so that we won't tweak (or show that we're tweaking) its offset
        # Even if it wouldn't have practical consequences, it makes debugging easier
        needlesdone[n]= needlesrefined[n]

    # Now comes the encoding step, where we use the needle code
    if debug>2:
        print ("####################################\nNow encoding\n####################################\n")

    # restore the haystack, as we did some replacements
    encoded=haystackin
    # restore the needles, as we did some tweaking on their positions
    needlesrefined=needlesrefinedcopy
    # restore the needles done, to help with debugging
    needlesdone={}

    # Exactly as above, except:
    #  - nn (dictin[n] surrounded by the separator) replaces n in delta and replaced,
    #  - the delta computation is different to take that code into account
    for n in needlesrefined.keys():
        [[sstart, slen, sstop ]] =needlesrefined[n]
        nstart=int(sstart)
        nlen=int(slen)
        nstop=int(sstop)

        # Applying the needle means replacing a piece of text by another, surrounded by separators
        nn = str(separator_start) + str(dictin[n]) + str(separator_stop)

        # It needs to take into account the size difference:
        # Doing even one replacement may change the offsets of all subsequent needles
        # So we compute the delta, as before would be delta1:
        #delta1=  nlen - 1 +nstart -nstop
        # Except it would need to take into account delta 2:
        #delta2 = len(str(nn)) - 1 - nstop + nstart
        # NEW','ORLEANS : haystack
        # NEW ORLEANS   : delta1=-2  (between haystack and needle)
        # 01              delta2=-9  (between needle and encoded needle)
        #   123456789AB : delta =-11 (between haystack and encoded needle
        # delta=delta2-delta1
        # So we use directly the difference between the 2 entries:
        delta= len(nn) -nlen

        # We truncate to before, apply the string, truncate what's after, and glue it together
        # Just as before, but nn instead of n
        replaced= encoded[:nstart] + str(nn) + encoded[nstop+1:]

        if debug>2:
            print("Needle is '" + str(n) + "' when encoded is '" +str(separator_start) + str(dictin[n]) + str(separator_stop) + "', at nstart=" +str(nstart) + "\n")
            print("Delta=" + str(delta) +": len(nn)=" +str(len(nn)) + " -nlen=" +str(nlen) + "\n")
            print("Gluing encoded with delta=" +str(delta) + ":\n>" + str(encoded[:nstart]) + "<+>" + str(nn) + "<+>" + str(encoded[nstop+1:]) +"\n")
            print("replaced encoded =" +str(replaced))

        if delta != 0:
            if debug>2:
                print("Tweaking encoded needles position if needed")
            for m in needlesrefined.keys():
                if not n == m and not m in needlesdone.keys():
                    [[tstart, tlen, tstop]] = needlesrefined[m]
                    mstart = int(tstart)
                    mlen = int(tlen)
                    mstop = int(tstop)
                    # For any other needle starting after the current one, update its offsets,
                    # all that matters is the start position of each needle:
                    if mstart>nstart:
                        mstartnew=mstart+delta
                        mstopnew=mstop+delta
                        mnew = [str(mstartnew), str(mlen), str(mstopnew)]

                        if debug > 2:
                            print (str((mstart > nstart + len(dictin[n]))))
                            print('needle encoded ' + str(m) + ' was:' + str(needlesrefined[m]))
                            print('needle encoded ' + str(m) + ' now:' + str(mnew))

                        needlesrefined[m]=[mnew]

        # Apply the update for the next loop
        encoded=replaced

        # Add to the needles dones
        needlesdone[n]=needlesrefined[n]

        if debug > 2:
            print('needles done ' + str(needlesdone[n]))

    return (recovered,encoded)

print("Distance tolerance for pieces:")
print(piecedistancetolerance)
print("Size required for pieces:")
print(piecesizerequirement)

f1, a1 = brokenneedlealgorithm(needlesgeo, haystackgeo1)
print("Haystack used:")
print(haystackgeo1)
print("Needles found, with subsets:")
print(f1)
f1copy=f1.copy()
g1 = naiverefineneedles(f1)
print("Non subsetting neddles (naive approach):")
print(g1)
# to compare:
if debug>2:
    print("Remember: subsetting needles found:")
    print(f1copy)

print("Recovered haystack:")
recover1=haystackgeo1
for n in g1.keys():
    [[sstart, slen, sstop ]] =g1[n]
    nstart=int(sstart)
    nlen=int(slen)
    nstop=int(sstop)
    # need to append spaces at the beginning in case the length differs
    delta= nstop -nstart -nlen +1
    replaced= delta*' ' + recover1[:nstart] + str(n) + recover1[nstop+1:]
    recover1=replaced
print(recover1)

print ("Encoded haystack:")
# the delta is why we use recover
encoded1=recover1
for n in g1.keys():
    [[nstart, nlen, nstop ]] = g1[n]
    value=needlesgeo[n]
    leftpaddedvalue=value.rjust(int(nlen), " ")
    replaced= encoded1[:int(nstart)] + str(leftpaddedvalue) + recover1[int(nstop)+1:]
    encoded1=replaced
print(encoded1)
print ("Without spaces:")
print(" ".join(encoded1.split()))

print ("------------------------------")
f2, a2 = brokenneedlealgorithm(needlesgeo, haystackgeo2)
print("Haystack used:")
print(haystackgeo2)
print("Needles found, with subsets:")
print(f2)
f2copy=f2.copy()
g2 = naiverefineneedles(f2)
print("Non subsetting neddles (naive approach):")
print(g2)
if debug>2:
    print("Remember: subsetting needles found:")
    print(f2copy)

# Manual recovery of the haystack
if debug > 0:
    a=a2
    print("Alternatives per pos:")
    print(a)
    i = len(a)
    print("Detail per position from 0 to " + str(i))
    j = 0
    while j < i:
        print("@ " + str(j))
        if a[j] is None:
            print("None")
            # next
        else:
            k = len(a[j])
            l = 0
            while l < k:
                print(a[j][l])
                l = l + 1
        j = j + 1

print("Recovered haystack:")
recover2=haystackgeo2
for n in g2.keys():
    [[sstart, slen, sstop ]] =g2[n]
    nstart=int(sstart)
    nlen=int(slen)
    nstop=int(sstop)
    # need to append spaces at the beginning in case the length differs
    delta= nstop -nstart -nlen +1
    replaced= delta*' ' + recover2[:nstart] + str(n) + recover2[nstop+1:]
    recover2=replaced
print(recover2)

print ("Encoded haystack:")
# the delta is why we use recover
encoded2=recover2
for n in g2.keys():
    [[nstart, nlen, nstop ]] = g2[n]
    value=needlesgeo[n]
    leftpaddedvalue=value.rjust(int(nlen), " ")
    replaced= encoded2[:int(nstart)] + str(leftpaddedvalue) + recover2[int(nstop)+1:]
    encoded2=replaced
print(encoded2)
print ("Without spaces:")
print(" ".join(encoded2.split()))

print ("Using the apply function:")
haystackrecovered2,haystackencoded2=brokenneedleapply(needlesgeo,haystackgeo2,"{", "}")
print(haystackrecovered2)
print(haystackencoded2)

print ("------------------------------")
f3, a3 = brokenneedlealgorithm(needlesgeo, haystackgeo3)
print("Haystack used:")
print(haystackgeo3)
print("Needles found, with subsets:")
print(f3)
f3copy=f3.copy()
g3 = naiverefineneedles(f3)
print("Non subsetting neddles (naive approach):")
print(g3)
if debug>2:
    print("Remember: subsetting needles found:")
    print(f3copy)

# Manual recovery
if debug > 0:
    a=a3
    print("Alternatives per pos:")
    print(a)
    i = len(a)
    print("Detail per position from 0 to " + str(i))
    j = 0
    while j < i:
        print("@ " + str(j))
        if a[j] is None:
            print("None")
            # next
        else:
            k = len(a[j])
            l = 0
            while l < k:
                print(a[j][l])
                l = l + 1
        j = j + 1

print("Recovered haystack:")
recover3=haystackgeo3
for n in g3.keys():
    [[sstart, slen, sstop ]] =g3[n]
    nstart=int(sstart)
    nlen=int(slen)
    nstop=int(sstop)
    # need to append spaces at the beginning in case the length differs
    delta= nstop -nstart -nlen +1
    replaced= recover3[:nstart] + delta*' ' +  str(n) + recover3[nstop+1:]
    recover3=replaced
print(recover3)

# the delta is why we use recover
encoded3=recover3
print ("Encoded haystack:")
for n in g3.keys():
    [[sstart, slen, sstop ]] =g3[n]
    nstart=int(sstart)
    nlen=int(slen)
    nstop=int(sstop)
    value=needlesgeo[n]
    leftpaddedvalue=value.rjust(nstop-nstart+1, " ")
    replaced= encoded3[:int(nstart)] + str(leftpaddedvalue) + recover3[int(nstop)+1:]
    encoded3=replaced
print(encoded3)
print ("Without spaces:")
print(" ".join(encoded3.split()))

print ("Using the apply function:")
haystackrecovered3,haystackencoded3=brokenneedleapply(needlesgeo,haystackgeo3,"{", "}")
print(haystackrecovered3)
print(haystackencoded3)
