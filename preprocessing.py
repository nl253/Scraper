#!/usr/bin/env python
# -*- coding: utf-8 -*-

# NO DEPENDENCIES

# BORROWED:
# - DocumentCleaner (from goose and newspaper)
# - OutputFormatter (from goose and newspaper)

from re import compile
import re

punctuation = "£%$![]{}~#-+=>^&*`¬</"


class StringSanitizer():
    def __init__(self, text: str):
        assert type(text) is str, 'Type of text not str'
        self._text = text

    def _remove_punct(self):
        translator = str.maketrans(self._text, self._text, "#\~|£%$!()[]{}~#-+=>^&*`¬</")
        self._text.translate(translator)
        # self._text = re.compile("(([\n^])|(\\xa0?\n?\^?))+").sub(" ", self._text)
        return self

    def _remove_references(self):
        self._text = compile("\[\d+\]+").sub("", self._text)
        return self

    def _beautify(self):
        self._text = compile("[\n\t ]{2,}").sub(" ", self._text)
        return self

    def sanitize(self):
        jeturn self._beautify()._remove_punct()._remove_references()

    @property
    def text(self):
        return self._text


class HTMLSanitizer():
    def __init__(self, html: str):
        self._html = html

    def substitute_tag(self, tag: str, repl: str):
        self._html.replace("<{} ".format(tag), "<{} ".format(repl))

    def _clean_javascript(self):
        pat = re.compile("<script.*?</script>")
        self._html = pat.sub("", self._html)
        return self

    def _clean_css(self):
        pat = re.compile("<style.*?</style>")
        self._html = pat.sub("", self._html)
        return self

    def sanitize(self):
        self._clean_javascript()
        self._clean_css()
        return self

    @property
    def html(self):
        return self._html

    def get_link_density(self, elem):
        link_length = 0
        for i in elem.findall(".//a"):
            link_length += text_length(i)
        # if len(elem.findall(".//div") or elem.findall(".//p")):
        #    link_length = link_length
        total_length = text_length(elem)
        return float(link_length) / max(total_length, 1)

    def tags(self, node, *tag_names):
        for tag_name in tag_names:
            for e in node.findall('.//%s' % tag_name):
                yield e


class DocumentCleaner(object):
    def __init__(self, config, article):
        # config
        self.config = config

        # parser
        self.parser = self.config.get_parser()

        # article
        self.article = article

        # nodes to remove regexp
        self.remove_nodes_re = (
            "^side$|combx|retweet|mediaarticlerelated|menucontainer|"
            "navbar|storytopbar-bucket|utility-bar|inline-share-tools"
            "|comment|PopularQuestions|contact|foot|footer|Footer|footnote"
            "|cnn_strycaptiontxt|cnn_html_slideshow|cnn_strylftcntnt"
            "|^links$|meta$|shoutbox|sponsor"
            "|tags|socialnetworking|socialNetworking|cnnStryHghLght"
            "|cnn_stryspcvbx|^inset$|pagetools|post-attributes"
            "|welcome_form|contentTools2|the_answers"
            "|communitypromo|runaroundLeft|subscribe|vcard|articleheadings"
            "|date|^print$|popup|author-dropdown|tools|socialtools|byline"
            "|konafilter|KonaFilter|breadcrumbs|^fn$|wp-caption-text"
            "|legende|ajoutVideo|timestamp|js_replies"
        )
        self.regexp_namespace = "http://exslt.org/regular-expressions"
        self.nauthy_ids_re = "//*[re:test(@id, '%s', 'i')]" % self.remove_nodes_re
        self.nauthy_classes_re = "//*[re:test(@class, '%s', 'i')]" % self.remove_nodes_re
        self.nauthy_names_re = "//*[re:test(@name, '%s', 'i')]" % self.remove_nodes_re
        self.div_to_p_re = r"<(a|blockquote|dl|div|img|ol|p|pre|table|ul)"
        self.caption_re = "^caption$"
        self.google_re = " google "
        self.entries_re = "^[^entry-]more.*$"
        self.facebook_re = "[^-]facebook"
        self.facebook_braodcasting_re = "facebook-broadcasting"
        self.twitter_re = "[^-]twitter"
        self.tablines_replacements = ReplaceSequence() \
            .create("\n", "\n\n") \
            .append("\t") \
            .append("^\\s+$")

    def clean(self):
        doc_to_clean = self.article.doc
        doc_to_clean = self.clean_body_classes(doc_to_clean)
        doc_to_clean = self.clean_article_tags(doc_to_clean)
        doc_to_clean = self.clean_em_tags(doc_to_clean)
        doc_to_clean = self.remove_drop_caps(doc_to_clean)
        doc_to_clean = self.remove_scripts_styles(doc_to_clean)
        doc_to_clean = self.clean_bad_tags(doc_to_clean)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.caption_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.google_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.entries_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.facebook_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.facebook_braodcasting_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.twitter_re)
        doc_to_clean = self.clean_para_spans(doc_to_clean)
        doc_to_clean = self.div_to_para(doc_to_clean, 'div')
        doc_to_clean = self.div_to_para(doc_to_clean, 'span')
        return doc_to_clean

    def clean_body_classes(self, doc):
        # we don't need body classes
        # in case it matches an unwanted class all the document
        # will be empty
        elements = self.parser.getElementsByTag(doc, tag="body")
        if elements:
            self.parser.delAttribute(elements[0], attr="class")
        return doc

    def clean_article_tags(self, doc):
        articles = self.parser.getElementsByTag(doc, tag='article')
        for article in articles:
            for attr in ['id', 'name', 'class']:
                self.parser.delAttribute(article, attr=attr)
        return doc

    def clean_em_tags(self, doc):
        ems = self.parser.getElementsByTag(doc, tag='em')
        for node in ems:
            images = self.parser.getElementsByTag(node, tag='img')
            if len(images) == 0:
                self.parser.drop_tag(node)
        return doc

    def remove_drop_caps(self, doc):
        items = self.parser.css_select(doc, "span[class~=dropcap], span[class~=drop_cap]")
        for item in items:
            self.parser.drop_tag(item)

        return doc

    def remove_scripts_styles(self, doc):
        # remove scripts
        scripts = self.parser.getElementsByTag(doc, tag='script')
        for item in scripts:
            self.parser.remove(item)

        # remove styles
        styles = self.parser.getElementsByTag(doc, tag='style')
        for item in styles:
            self.parser.remove(item)

        # remove comments
        comments = self.parser.getComments(doc)
        for item in comments:
            self.parser.remove(item)

        return doc

    def clean_bad_tags(self, doc):
        # ids
        naughty_list = self.parser.xpath_re(doc, self.nauthy_ids_re)
        for node in naughty_list:
            self.parser.remove(node)

        # class
        naughty_classes = self.parser.xpath_re(doc, self.nauthy_classes_re)
        for node in naughty_classes:
            self.parser.remove(node)

        # name
        naughty_names = self.parser.xpath_re(doc, self.nauthy_names_re)
        for node in naughty_names:
            self.parser.remove(node)

        return doc

    def remove_nodes_regex(self, doc, pattern):
        for selector in ['id', 'class']:
            reg = "//*[re:test(@%s, '%s', 'i')]" % (selector, pattern)
            naughty_list = self.parser.xpath_re(doc, reg)
            for node in naughty_list:
                self.parser.remove(node)
        return doc

    def clean_para_spans(self, doc):
        spans = self.parser.css_select(doc, 'p span')
        for item in spans:
            self.parser.drop_tag(item)
        return doc

    def get_flushed_buffer(self, replacement_text, doc):
        return self.parser.textToPara(replacement_text)

    def get_replacement_nodes(self, doc, div):
        replacement_text = []
        nodes_to_return = []
        nodes_to_remove = []
        childs = self.parser.childNodesWithText(div)

        for kid in childs:
            # node is a p
            # and already have some replacement text
            if self.parser.getTag(kid) == 'p' and len(replacement_text) > 0:
                newNode = self.get_flushed_buffer(''.join(replacement_text), doc)
                nodes_to_return.append(newNode)
                replacement_text = []
                nodes_to_return.append(kid)
            # node is a text node
            elif self.parser.isTextNode(kid):
                kid_text_node = kid
                kid_text = self.parser.getText(kid)
                replace_text = self.tablines_replacements.replaceAll(kid_text)
                if (len(replace_text)) > 1:
                    previous_sibling_node = self.parser.previousSibling(kid_text_node)
                    while previous_sibling_node is not None \
                            and self.parser.getTag(previous_sibling_node) == "a" \
                            and self.parser.getAttribute(previous_sibling_node, 'grv-usedalready') != 'yes':
                        outer = " " + self.parser.outerHtml(previous_sibling_node) + " "
                        replacement_text.append(outer)
                        nodes_to_remove.append(previous_sibling_node)
                        self.parser.setAttribute(previous_sibling_node,
                                                 attr='grv-usedalready', value='yes')
                        prev = self.parser.previousSibling(previous_sibling_node)
                        previous_sibling_node = prev if prev is not None else None
                    # append replace_text
                    replacement_text.append(replace_text)
                    #
                    next_sibling_node = self.parser.nextSibling(kid_text_node)
                    while next_sibling_node is not None \
                            and self.parser.getTag(next_sibling_node) == "a" \
                            and self.parser.getAttribute(next_sibling_node, 'grv-usedalready') != 'yes':
                        outer = " " + self.parser.outerHtml(next_sibling_node) + " "
                        replacement_text.append(outer)
                        nodes_to_remove.append(next_sibling_node)
                        self.parser.setAttribute(next_sibling_node,
                                                 attr='grv-usedalready', value='yes')
                        next = self.parser.nextSibling(next_sibling_node)
                        previous_sibling_node = next if next is not None else None

            # otherwise
            else:
                nodes_to_return.append(kid)

        # flush out anything still remaining
        if (len(replacement_text) > 0):
            new_node = self.get_flushed_buffer(''.join(replacement_text), doc)
            nodes_to_return.append(new_node)
            replacement_text = []

        for n in nodes_to_remove:
            self.parser.remove(n)

        return nodes_to_return

    def replace_with_para(self, doc, div):
        self.parser.replaceTag(div, 'p')

    def div_to_para(self, doc, dom_type):
        bad_divs = 0
        else_divs = 0
        divs = self.parser.getElementsByTag(doc, tag=dom_type)
        tags = ['a', 'blockquote', 'dl', 'div', 'img', 'ol', 'p', 'pre', 'table', 'ul']

        for div in divs:
            items = self.parser.getElementsByTags(div, tags)
            if div is not None and len(items) == 0:
                self.replace_with_para(doc, div)
                bad_divs += 1
            elif div is not None:
                replaceNodes = self.get_replacement_nodes(doc, div)
                for child in self.parser.childNodes(div):
                    div.remove(child)

                for c, n in enumerate(replaceNodes):
                    div.insert(c, n)

                else_divs += 1

        return doc

    def sanitize(self, node, candidates):
        MIN_LEN = self.min_text_length
        for header in self.tags(node, "h1", "h2", "h3", "h4", "h5", "h6"):
            if self.class_weight(header) < 0 or self.get_link_density(header) > 0.33:
                header.drop_tree()

        for elem in self.tags(node, "form", "textarea"):
            elem.drop_tree()

        for elem in self.tags(node, "iframe"):
            if "src" in elem.attrib and REGEXES["videoRe"].search(elem.attrib["src"]):
                elem.text = "VIDEO"  # ADD content to iframe text node to force <iframe></iframe> proper output
            else:
                elem.drop_tree()

        allowed = {}
        # Conditionally clean <table>s, <ul>s, and <div>s
        for el in self.reverse_tags(node, "table", "ul", "div"):
            if el in allowed:
                continue
            weight = self.class_weight(el)
            if el in candidates:
                content_score = candidates[el]['content_score']
                # print '!',el, '-> %6.3f' % content_score
            else:
                content_score = 0
            tag = el.tag

            if weight + content_score < 0:
                log.debug("Removed %s with score %6.3f and weight %-3s" %
                          (describe(el), content_score, weight,))
                el.drop_tree()
            elif el.text_content().count(",") < 10:
                counts = {}
                for kind in ['p', 'img', 'li', 'a', 'embed', 'input']:
                    counts[kind] = len(el.findall('.//%s' % kind))
                counts["li"] -= 100
                counts["input"] -= len(el.findall('.//input[@type="hidden"]'))

                # Count the text length excluding any surrounding whitespace
                content_length = text_length(el)
                link_density = self.get_link_density(el)
                parent_node = el.getparent()
                if parent_node is not None:
                    if parent_node in candidates:
                        content_score = candidates[parent_node]['content_score']
                    else:
                        content_score = 0
                        # if parent_node is not None:
                        # pweight = self.class_weight(parent_node) + content_score
                        # pname = describe(parent_node)
                        # else:
                        # pweight = 0
                        # pname = "no parent"
                to_remove = False
                reason = ""

                # if el.tag == 'div' and counts["img"] >= 1:
                #    continue
                if counts["p"] and counts["img"] > 1 + counts["p"] * 1.3:
                    reason = "too many images (%s)" % counts["img"]
                    to_remove = True
                elif counts["li"] > counts["p"] and tag != "ul" and tag != "ol":
                    reason = "more <li>s than <p>s"
                    to_remove = True
                elif counts["input"] > (counts["p"] / 3):
                    reason = "less than 3x <p>s than <input>s"
                    to_remove = True
                elif content_length < MIN_LEN and counts["img"] == 0:
                    reason = "too short content length %s without a single image" % content_length
                    to_remove = True
                elif content_length < MIN_LEN and counts["img"] > 2:
                    reason = "too short content length %s and too many images" % content_length
                    to_remove = True
                elif weight < 25 and link_density > 0.2:
                    reason = "too many links %.3f for its weight %s" % (
                        link_density, weight)
                    to_remove = True
                elif weight >= 25 and link_density > 0.5:
                    reason = "too many links %.3f for its weight %s" % (
                        link_density, weight)
                    to_remove = True
                elif (counts["embed"] == 1 and content_length < 75) or counts["embed"] > 1:
                    reason = "<embed>s with too short content length, or too many <embed>s"
                    to_remove = True
                elif not content_length:
                    reason = "no content"
                    to_remove = True
                    #                if el.tag == 'div' and counts['img'] >= 1 and to_remove:
                    #                    imgs = el.findall('.//img')
                    #                    valid_img = False
                    #                    log.debug(tounicode(el))
                    #                    for img in imgs:
                    #
                    #                        height = img.get('height')
                    #                        text_length = img.get('text_length')
                    #                        log.debug ("height %s text_length %s" %(repr(height), repr(text_length)))
                    #                        if to_int(height) >= 100 or to_int(text_length) >= 100:
                    #                            valid_img = True
                    #                            log.debug("valid image" + tounicode(img))
                    #                            break
                    #                    if valid_img:
                    #                        to_remove = False
                    #                        log.debug("Allowing %s" %el.text_content())
                    #                        for desnode in self.tags(el, "table", "ul", "div"):
                    #                            allowed[desnode] = True

                    # find x non empty preceding and succeeding siblings
                    i, j = 0, 0
                    x = 1
                    siblings = []
                    for sib in el.itersiblings():
                        # log.debug(sib.text_content())
                        sib_content_length = text_length(sib)
                        if sib_content_length:
                            i = + 1
                            siblings.append(sib_content_length)
                            if i == x:
                                break
                    for sib in el.itersiblings(preceding=True):
                        # log.debug(sib.text_content())
                        sib_content_length = text_length(sib)
                        if sib_content_length:
                            j = + 1
                            siblings.append(sib_content_length)
                            if j == x:
                                break
                    # log.debug(str_(siblings))
                    if siblings and sum(siblings) > 1000:
                        to_remove = False
                        log.debug("Allowing %s" % describe(el))
                        for desnode in self.tags(el, "table", "ul", "div"):
                            allowed[desnode] = True

                if to_remove:
                    log.debug("Removed %6.3f %s with weight %s cause it has %s." %
                              (content_score, describe(el), weight, reason))
                    # print tounicode(el)
                    # log.debug("pname %s pweight %.3f" %(pname, pweight))
                    el.drop_tree()
                else:
                    log.debug("Not removing %s of length %s: %s" % (
                        describe(el), content_length, text_content(el)))

        self.html = node
        return self.get_clean_html()


class OutputFormatter(object):
    def __init__(self, config, article):
        # config
        self.config = config

        # article
        self.article = article

        # parser
        self.parser = self.config.get_parser()

        # stopwords class
        self.stopwords_class = config.stopwords_class

        # top node
        self.top_node = None

    def get_language(self):
        """\
        Returns the language is by the article or
        the configuration language
        """
        # we don't want to force the target language
        # so we use the article.meta_lang
        if self.config.use_meta_language:
            if self.article.meta_lang:
                return self.article.meta_lang[:2]
        return self.config.target_language

    def get_top_node(self):
        return self.top_node

    def get_formatted_text(self):
        self.top_node = self.article.top_node
        self.remove_negativescores_nodes()
        self.links_to_text()
        self.add_newline_to_br()
        self.replace_with_text()
        self.remove_fewwords_paragraphs()
        return self.convert_to_text()

    def convert_to_text(self):
        txts = []
        for node in list(self.get_top_node()):
            txt = self.parser.getText(node)
            if txt:
                txt = HTMLParser().unescape(txt)
                txt_lis = innerTrim(txt).split(r'\n')
                txts.extend(txt_lis)
        return '\n\n'.join(txts)

    def add_newline_to_br(self):
        for e in self.parser.getElementsByTag(self.top_node, tag='br'):
            e.text = r'\n'

    def links_to_text(self):
        """\
        cleans up and converts any nodes that
        should be considered text into text
        """
        self.parser.stripTags(self.get_top_node(), 'a')

    def remove_negativescores_nodes(self):
        """\
        if there are elements inside our top node
        that have a negative gravity score,
        let's give em the boot
        """
        gravity_items = self.parser.css_select(self.top_node, "*[gravityScore]")
        for item in gravity_items:
            score = self.parser.getAttribute(item, 'gravityScore')
            score = int(score, 0)
            if score < 1:
                item.getparent().remove(item)

    def replace_with_text(self):
        """\
        replace common tags with just
        text so we don't have any crazy formatting issues
        so replace <br>, <i>, <strong>, etc....
        with whatever text is inside them
        code : http://lxml.de/api/lxml.etree-module.html#strip_tags
        """
        self.parser.stripTags(self.get_top_node(), 'b', 'strong', 'i', 'br', 'sup')

    def remove_fewwords_paragraphs(self):
        """\
        remove paragraphs that have less than x number of words,
        would indicate that it's some sort of link
        """
        all_nodes = self.parser.getElementsByTags(self.get_top_node(), ['*'])
        all_nodes.reverse()
        for el in all_nodes:
            tag = self.parser.getTag(el)
            text = self.parser.getText(el)
            stop_words = self.stopwords_class(language=self.get_language()).get_stopword_count(text)
            if (tag != 'br' or text != '\\r') and stop_words.get_stopword_count() < 3 \
                    and len(self.parser.getElementsByTag(el, tag='object')) == 0 \
                    and len(self.parser.getElementsByTag(el, tag='embed')) == 0:
                self.parser.remove(el)
            # TODO
            # check if it is in the right place
            else:
                trimmed = self.parser.getText(el)
                if trimmed.startswith("(") and trimmed.endswith(")"):
                    self.parser.remove(el)
