# FIXME Replace HtmlResponse with lxml or something for performance.
from ..settings import SUMMER_URL, SUMMER_SUBMIT_URL
from .parsers import LessonParser, SummerParser

from abc import ABCMeta, abstractmethod
import logging
import requests

logger = logging.getLogger(__name__)


class Spider(object, metaclass=ABCMeta):
    # Misssing: url, SUBMIT_URL, session_config, parser_config

    def __init__(self, session):
        self.session = session
        self.__refresh_parser()

    def _get(self, *args, **kwargs):
        return self.session.get(url=self.url, *args, **kwargs)

    def _post(self, data, *args, **kwargs):
        ''' 用self.url和asp_dict包装一下session的post，自动带上__VIEWSTATE之类
            的东西
        '''
        while True:
            try:
                return self.session.post(url=self.url,
                                         data=data,
                                         asp_dict=self.asp_dict,
                                         *args,
                                         **kwargs)
            except requests.exceptions.HTTPError:
                logger.error("asp arguments expired.")
                self.__refresh_parser()

    def __refresh_parser(self):
        ''' 如果__VIEWSTATE之类的东西过期了就调用这个
        '''
        # FIXME: Use a parser factory here.
        self.parser = SummerParser(self._get())
        self.asp_dict = self.parser.get_asp_args()

    def get_current_number_by_course_id(self, course_id):
        ''' 给一个cid，查询当前改课所有老师的选课人数
        '''
        for info in self.crawl_by_course_id(course_id):
            yield {info['bsid']: info['now_number']}

    @abstractmethod
    def crawl_one_course_by_course_id(self, course_id):
        ''' 根据课程代码爬课的信息
            @params course_id: 课程代码，比如AD001
            @return 一个课程信息生成器，信息格式见lesson_page.py
        '''
        pass

    @abstractmethod
    def crawl(self):
        ''' 爬所有课程信息，
            @params course_id: 课程代码，比如AD001
            @return 一个课程信息生成器, 数据格式见wiki
        '''
        pass


class SummerSpider(Spider):
    url = SUMMER_URL
    SUBMIT_URL = SUMMER_SUBMIT_URL

    def crawl_one_course_by_course_id(self, course_id):
        inner_parser = LessonParser(self._post({'myradiogroup': course_id,
                                                'lessonArrange': '课程安排'}))
        outer_info = self.__search_outer_info_by_course_id(course_id)
        for inner_info in inner_parser.parse():
            inner_info.update(outer_info)
            yield inner_info

    # FIXME: 这个代码重复修一下.
    def crawl(self):
        for outer_info in self.parser.parse():
            inner_parser = LessonParser(self._post(data={'myradiogroup':
                                                         outer_info['cid'],
                                                         'lessonArrange':
                                                         '课程安排'}))
            for inner_info in inner_parser.parse():
                inner_info.update(outer_info)
                yield inner_info

    def __search_outer_info_by_course_id(self, course_id):
        for outer_info in self.parser.parse():
            if outer_info['cid'] == course_id:
                return outer_info
        raise ValueError("Course Id %s not found" % course_id)

# class SpiderFactory(PageFactory):
#     def create(self, description):
#         if description == 'summer':
#             return SummerSpider(self.session)
#         else:
#             raise TypeError("ListPage has no type %s" % description)
