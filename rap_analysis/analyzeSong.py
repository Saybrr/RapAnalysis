"""
Juno Mayer
A test of kevin brown's rhyme detection  
takes lyrics, tokenizes them, prints them out to console with marks to deliminate rhymes

"""
import os 
from rhyme_detect import rhymes, scheme, syllables
import sys
import pprint
from copy import deepcopy
import nltk
import logging
import time

logging.basicConfig(level=logging.INFO)

phone_dictionary = nltk.corpus.cmudict.dict()

def possible_phones(word):

    if word not in phone_dictionary:
        return []
    return phone_dictionary[word]


def phon_match(first_phon : list, second_phon : list,start : int, end: int,debug=False) -> int:
    logging.debug(f"FIRST: {first_phon} SECOND: {second_phon}")
    first_range = first_phon[start:end]
    second_range = second_phon[start:end]

    first_range = first_range[::-1]
    second_range = second_range[::-1]

    if debug:
        logging.debug(f"FIRST RANGE: {first_range}, SECOND RANGE: {second_range}")

    if len(first_range) > len(second_range):
        first_range, second_range = second_range, first_range

    hits = 0
    total = len(first_range)

    for idx, phone in enumerate(first_range):
        other_phone = second_range[idx]

        if phone == other_phone:
            hits += 1

            # Phones with emphasis are better matches, weight them more
            if phone[-1].isdigit():
                hits += 1
                total += 1

    return hits/total

def word_similarity(first_word, second_word, start_phone=None, end_phone=None,debug=False):
    # print(f"looking up Phonemes for {first_word} and {second_word}")
    first_phones = possible_phones(first_word)
    second_phones = possible_phones(second_word)

    if not first_phones or not second_phones:
        return 0

    #just use first pronounciation of the words

    if len(first_phones) + len(second_phones) == 2:
        first_phones = first_phones[0]
        second_phones = second_phones[0] 
        return phon_match(first_phones, second_phones,start_phone,end_phone,debug=True)
    
    else:
    #we want to find if any pronouciations result in a rhyme
        scorelist = []
        for f_p in first_phones:
            for s_p in second_phones: 
                scorelist.append(phon_match(f_p,s_p,start_phone,end_phone,debug=True))
            
        if 1 in scorelist:
            return 1
        else: 
            return 0



def mark_with_rhymes(lyrics : str, delims : dict) -> str: 
    """
    marks the lyrics with delims around words based on rhymes 
    """
    #split lyrics string by newline to create a list by line 
    #split each line by space to get a list of lists 
    #create copy to iterate through and remove already processed 
    split_lyrics = []
    d = '\n'
    split_lyrics = lyrics.lower().split()
    split_lyrics = [l.strip(",?\"'.") for l in split_lyrics]
    logging.debug(split_lyrics)

    # for line in lines: 
    #     split_lyrics.append(line.split())
    #make copy unique to remove repeated lines 
    iter_copy = deepcopy(split_lyrics)
    iter_copy = list(set(iter_copy))
    mark_copy = deepcopy(split_lyrics)

    found_rhymes = 0 
    prev_found = 0
    for word in split_lyrics:
        found = False
        iter_seg = iter_copy[split_lyrics.index(word)-20:split_lyrics.index(word)+20]
        for cpyword in iter_copy:
    #       if word similarity(word, copyword) > 0 then its a rhyme
            if word != cpyword: 
                # we are concerned with end rhymes for now, only want to check if the last phoneme in the word matches
                # so start at the last phoneme of the shortest word (length of shortest - 1 OR 1 if its a 1 phoneme word)
                word_phon = possible_phones(word)
                cpyword_phon = possible_phones(cpyword)
                if word_phon == []: 
                    logging.debug(f"word {word} was not found in CMUDict")
                elif cpyword_phon == []: 
                    logging.debug(f"cpyword {cpyword} was not found in CMUDict")
                    iter_copy.remove(cpyword)
                else:
                    shortest_word_phon = min(word_phon, key=len)
                    shortest_cpy_phon = min(cpyword_phon, key=len)
                    shortest_phon = min([shortest_cpy_phon,shortest_word_phon], key=len)
                    # word_phon if len(word_phon[0]) <= len(cpyword_phon[0]) else cpyword_phon

                    logging.debug(f"WORD: {word} {word_phon}, CPYWORD: {cpyword} {cpyword_phon}, SHORTEST: {shortest_phon}")
                    logging.debug(f"{len(shortest_phon)} phonemes in {shortest_phon}")
                    # if we have a 1 phoneneme word, we dont subtract off the end (last phoneme is the only phoneme)
                    nphones_in_shortest = 0 if (len(shortest_phon) - 1) == 0 else len(shortest_phon) - 1
                    
                    if word_similarity(word,cpyword, start_phone=nphones_in_shortest, debug=True) == 1:
                        found = True
                        #rhyme is between WORD in splitlyrics (original) and some other word (CPYWORD) in the iter_copy
                        #mark both words in rhyme pair with the same number 
                        delimnated_word = str(found_rhymes) + word + str(found_rhymes)
                        delimnated_cpy = str(found_rhymes) + cpyword + str(found_rhymes)
                        # replace the word that rhymes with a delimnated version of it
                        try:
                            # if it is not marked yet, we can use the original word
                            mark_copy[mark_copy.index(cpyword)] = delimnated_cpy
                            mark_copy[mark_copy.index(word)] = delimnated_word
                        except ValueError:
                            # if we dont find the word, its because its already been marked 
                            logging.debug(f"{cpyword} alerady marked by another rhyme")

                        logging.debug(f"word {delimnated_word} rhymes with {delimnated_cpy}")
                        #delete it so we save time
                        iter_copy.remove(cpyword)
                
            logging.debug(80 * '-')
        if found: 
            # this word did not rhyme and has not been delimnated / appended
            found_rhymes += 1 
        
    return mark_copy

# def format_as_lyrics(marked : list, lyrics: str):
#     """
#     reads a list and a string, formats the list like the string
#     """
#     formatted = ""

#     for i in range


def main():

    # string of delimiters of which to place aro
    # und words when rhymes are found
    # pairs: () [] {} || ** %% ^^ @@ $$ && -- __ 
    delims = {0:['(',')'],
             1:['{','}'],
             2:['[',']'],
             3:['/','/'],
             4:['<','>'],
             5:['!','!'],
             6:['@','@'],
             7:['$','$'],
             8:['*','*'],
             9:['^','^']}


    lyrics = open(sys.argv[1],'r').read()


    tic = time.perf_counter()
    marked = mark_with_rhymes(lyrics, delims)
    toc = time.perf_counter()
    logging.info(f"{toc - tic} seconds for one song")

    tic = time.perf_counter()
    for i in range(100):
        marked = mark_with_rhymes(lyrics, delims)
    toc = time.perf_counter()     

    logging.info(f"{toc - tic} seconds for 100 song, {len(marked)} words")

    print(marked)
    # print(marked)


if __name__ == "__main__":
    main()



    # for i in range(len(split_lyrics)):
    #     if d in split_lyrics[i]:
    #         print(split_lyrics[i])
    #         words_with_newl = [e+d for e in split_lyrics[i].split(d) if e] 
    #         split_lyrics.remove(split_lyrics[i]) 
    #         for word in words_with_newl:
    #             split_lyrics.insert(i,word)



# ['(rap)', 'snitches,', '{telling}', '[all]', '/their/', '<business>',
#  'Sit', '{in}', '@the@', '@court@', '*and*', '^be^', 'their', '!own!', '/star/', '<witness>',
#   'Do', '[you]', '^see^', 'the', 'perpetrator?', 'Yeah,', "I'm", '(right)', '/here/',
#   'Fuck', 'around,', '/get/', 'the', '[whole]', '[label]', '*sent*', '(up)', '[for]', '{years}',
   



#    ['0rap0', 'snitches', '1telling1', '2all2', '3their3', '4business4', 
#    '5sit5', '6in6', '7the7', '5court5', '9and9', '10be10', '3their3', '6own6', '3star3', '4witness4', 
#    '14do14', '14you14', '10see10', '7the7', '17perpetrator17', 'yeah', "18i'm18", '5right5', '3here3',
#     '19fuck19', '9around9', '5get5', '26the26', '2whole2', '2label2', '5sent5', '0up0', '3for3', '23years23',

#      '0type0', '2profile2', '24low24', '19like19', '7a7', '6in6', '9paid9', '6in6', '2full2', 
#      '8attract8', '28heavy28', 'cash', '23cause23', 'the', "23game's23", '2centrifugal2',

#     '17mr17', '19fantastik19', '1long1', '24dough24', '25like25', '25elastic25',
#     '9guard9', '33my33', '34life34', 'with', '6twin6', 'glocks', "4that's4", '20made20', '5out5', 'of', '19plastic19',

#     "5can't5", '9stand9', '26a26', '6brown6', '31nosing31', 'nigga', '19fake19', '4ass4', '9bastard9',
#     '1admiring1', '38my38', '2style2', '3tour3', '13bus13', '14through14', '6manhattan6',

#     '1plotting1', '6plan6', 'the', '5quickest5', 'my', "flow's", 'the', '5sickest5',
#      'my', '23hoes23', '10be10', 'the', '5thickest5', 'my', 'dro', 'the', '5stickiest5',

#     '8street8', 'nigga', '5stamped5', '9and9', '9bonafide9', 
#     '6when6', '34beef34', '0jump0', 'niggas', '40come40', 'get', '10me10', '29cause29', '37they37', '24know24', '33i33', '9ride9',

#     '14true14', '14to14', 'the', '10ski10', '19mask19', '14new14', "4york's4", 'my', '11origin11', 
#     '37play37', 'a', 'fake', '7gangsta7', 'like', 'a', '9old9', '6accordion6', 
#     '1according1', 'to', '18him18', 'when', 'the', "29d's29", '5rushed5', '6in6', 
#     '6complication6', '18from18', 'the', '17wire17', '28testimony28', '23was23', '6thin6', 
#     '9caused9', '23his23', '6man6', 'to', '24go24', 'up', 'north', 'the', '2ball2', '5hit5', '18em18', '6again6', 
#     '18lame18', '0rap0', 'snitch', 'nigga', '6even6', '20told20', '11on11', 'the', '11mexican11']


# ['0rap0', 'snitches', '1telling1', '2all2', '3their3', '4business4', 
# '5sit5', '6in6', '7the7', '5court5', '9and9', '7be7', '3their3', '6own6', '3star3', '4witness4', 

# '14do14', '14you14', '10see10', '7the7', '16perpetrator16', 'yeah', "17i'm17", '5right5', '3here3',
#  '18fuck18', '6around6', '5get5', '7the7', '2whole2', '2label2', '5sent5', '0up0', '16for16', '24years24',

#   '0type0', '2profile2', '25low25', '18like18', '7a7', '6in6', '9paid9', '6in6', '2full2',
#    '5attract5', '7heavy7', 'cash', '24cause24', '7the7', "24game's24", '2centrifugal2', 

#    '16mr16', '18fantastik18', '1long1', '25dough25', 'like', '18elastic18', 
#    '9guard9', '32my32', '33life33', '34with34', '11twin11', 'glocks', "4that's4", '9made9', '5out5', 'of', '18plastic18',

#     "5can't5", '9stand9', '27a27', '6brown6', '1nosing1', 'nigga', '18fake18', '4ass4', '28bastard28',
#     '1admiring1', '37my37', '21style21', '3tour3', '4bus4', '14through14', '6manhattan6', 

#     '1plotting1', '6plan6', '7the7', '5quickest5', 'my', "flow's", '7the7', '5sickest5',
#      'my', '24hoes24', '10be10', '10the10', '5thickest5', 'my', 'dro', 'the', '5stickiest5', 

#      '5street5', 'nigga', '5stamped5', '9and9', '9bonafide9', 
#      '6when6', '33beef33', '22jump22', 'niggas', '17come17', 'get', '10me10', 'cause', '27they27', '25know25', '32i32', '9ride9',
     
#       '14true14', '7to7', 'the', '10ski10', '18mask18', '14new14', "13york's13", 'my', '6origin6',
#      '27play27', '27a27', 'fake', '7gangsta7', 'like', 'a', '9old9', '11accordion11', 
#      '1according1', 'to', '17him17', 'when', 'the', "24d's24", '5rushed5', '6in6', 
#      '6complication6', '17from17', 'the', '3wire3', '7testimony7', '24was24', '6thin6',
#       '9caused9', '24his24', '6man6', 'to', '25go25', '22up22', '34north34', 'the', '2ball2', '5hit5', '17em17', '6again6',
#        '17lame17', '0rap0', 'snitch', 'nigga', '6even6', '9told9', '6on6', 'the', '6mexican6']