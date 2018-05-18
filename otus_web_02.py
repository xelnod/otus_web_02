import dateparser
import requests
import pymorphy2
import collections
import argparse
from prettytable import PrettyTable
from datetime import timedelta
from bs4 import BeautifulSoup

from config import HABR_URL, KNOWN_PYMORPHY_MISTAKES


def get_habr_html(page=None):
    url = HABR_URL + 'page%s/' % page if page else HABR_URL
    r = requests.get(url)
    if r.ok:
        return r.content


def get_articles_info_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    articles = soup.findAll("article", {"class": "post post_preview"})
    return (
        [(a.find("a", {"class": "post__title_link"}).text,
          a.find("span", {"class": "post__time"}).text) for a in articles]
    )


def is_noun(word):
    return 'NOUN' in word.tag


def arrange_articles_into_weeks(article_titles_with_dates, morph):
    weeks = {}
    for title, date_str in article_titles_with_dates:
        date = dateparser.parse(date_str)
        week_num = date.isocalendar()[1]
        if week_num not in weeks:
            week_start = (date - timedelta(days=date.weekday())).date()
            week_end = (week_start + timedelta(days=6))
            weeks[week_num] = {'nouns': [], 'date_start': week_start, 'date_end': week_end}
        weeks[week_num]['nouns'] += get_nouns_from_article_title(title, morph)
    return weeks


def get_nouns_from_article_title(article_title, morph):
    nouns = []
    for word in article_title.split():
        word_parsed = morph.parse(word.strip('«»."()?,:'))[0]
        if is_noun(word_parsed):
            normalized_word = KNOWN_PYMORPHY_MISTAKES.get(word_parsed.normal_form, word_parsed.normal_form)
            nouns.append(normalized_word)
    return nouns


def count_nouns_in_weeks(weeks, top_size=3):
    _weeks = weeks.copy()
    for week_num in _weeks.keys():
        top_nouns = collections.Counter(_weeks[week_num]['nouns']).most_common(top_size)
        _weeks[week_num]['nouns'] = [noun[0] for noun in top_nouns]
    return _weeks


def print_weeks(weeks_dict, top_size):
    output_table = PrettyTable(field_names=["Week Start", "Week End", "Top %s Nouns" % top_size])
    for key in sorted(weeks_dict.keys()):
        output_table.add_row([weeks_dict[key]['date_start'],
                              weeks_dict[key]['date_end'],
                              ' '.join(weeks_dict[key]['nouns'])])
    print(output_table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', metavar='pages', type=int, nargs='?', default=50,
                        help='number of pages to parse, default is 50')
    parser.add_argument('--top_size', metavar='top_size', type=int, nargs='?', default=3,
                        help='number of most common words to find, default is 3')
    args = parser.parse_args()

    pages_num = args.pages
    article_titles_with_dates = []
    for page in range(pages_num):
        habr_html = get_habr_html(page)
        if habr_html:
            article_titles_with_dates += (get_articles_info_from_html(habr_html))
    morph = pymorphy2.MorphAnalyzer()
    weeks_numerated = arrange_articles_into_weeks(article_titles_with_dates, morph)
    weeks_with_top_n_nouns = count_nouns_in_weeks(weeks_numerated, top_size=args.top_size)
    print_weeks(weeks_with_top_n_nouns, top_size=args.top_size)
