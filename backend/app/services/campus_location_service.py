from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal
from urllib.parse import quote


CampusLocationType = Literal[
    "teaching_building", "library", "canteen", "dormitory", "gate", "sports", "office", "lab", "other",
]


@dataclass(frozen=True)
class CampusLocation:
    id: str
    name: str
    aliases: list[str]
    type: CampusLocationType
    campus: str = "nanwangshan"
    latitude: float = 0.0
    longitude: float = 0.0
    description: str = ""
    address: str = ""
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            object.__setattr__(self, 'tags', [])

    def to_dict(self) -> dict:
        data = asdict(self)
        data["mapUrl"] = build_map_url(self)
        return data


# Campus navigation POIs are corrected from the names provided by the user.
# Coordinates come from AMap Place Text API and are directly usable by AMap JS/routing.
CAMPUS_LOCATIONS: list[CampusLocation] = [
    CampusLocation(
        id='amap-poi-01',
        name='中国地质大学未来城校区资环工研院',
        aliases=['中国地质大学未来城校区资环工研院'],
        type='lab',
        campus='future_city',
        latitude=30.45868,
        longitude=114.612655,
        description='高德地图公开 POI：中国地质大学未来城校区资环工研院。',
        address='东湖新技术开发区锦程街68号中国地质大学未来城校区',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-02',
        name='武汉地质资源环境工业技术研究院园区',
        aliases=['武汉地质资源环境工业技术研究院园区'],
        type='lab',
        campus='future_city',
        latitude=30.458175,
        longitude=114.613325,
        description='高德地图公开 POI：武汉地质资源环境工业技术研究院园区。',
        address='左庙路中国地质大学(未来城校区)',
        tags=['科教文化服务', '科教文化场所', '科教文化场所'],
    ),
    CampusLocation(
        id='amap-poi-03',
        name='中国地质大学未来城校区经济管理学院',
        aliases=['中国地质大学未来城校区经济管理学院'],
        type='office',
        campus='future_city',
        latitude=30.458548,
        longitude=114.614572,
        description='高德地图公开 POI：中国地质大学未来城校区经济管理学院。',
        address='东湖新技术开发区锦程街68号中国地质大学未来城校区',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-04',
        name='中国地质大学未来城校区材料与化学学院',
        aliases=['中国地质大学未来城校区材料与化学学院'],
        type='office',
        campus='future_city',
        latitude=30.45843,
        longitude=114.616211,
        description='高德地图公开 POI：中国地质大学未来城校区材料与化学学院。',
        address='东湖新技术开发区锦程街68号中国地质大学未来城校区',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-05',
        name='中国地质大学未来城校区环境学院',
        aliases=['中国地质大学未来城校区环境学院'],
        type='office',
        campus='future_city',
        latitude=30.457458,
        longitude=114.615565,
        description='高德地图公开 POI：中国地质大学未来城校区环境学院。',
        address='东湖新技术开发区左岭锦程街68号',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-06',
        name='中国地质大学未来城校区生物地质与环境地质国家重点实验室',
        aliases=['中国地质大学未来城校区生物地质与环境地质国家重点实验室'],
        type='lab',
        campus='future_city',
        latitude=30.457879,
        longitude=114.617385,
        description='高德地图公开 POI：中国地质大学未来城校区生物地质与环境地质国家重点实验室。',
        address='湖北省武汉市洪山区左庙路',
        tags=['科教文化服务', '科教文化场所', '科教文化场所'],
    ),
    CampusLocation(
        id='amap-poi-07',
        name='中国地质大学(武汉)未来城-地球广场',
        aliases=['中国地质大学(武汉)未来城-地球广场'],
        type='other',
        campus='future_city',
        latitude=30.45639,
        longitude=114.616758,
        description='高德地图公开 POI：中国地质大学(武汉)未来城-地球广场。',
        address='左庙路中国地质大学(未来城校区)',
        tags=['风景名胜', '公园广场', '城市广场'],
    ),
    CampusLocation(
        id='amap-poi-08',
        name='中国地质大学未来城校区学生宿舍一组团3栋',
        aliases=['中国地质大学未来城校区学生宿舍一组团3栋', '中国地质大学未来城校区学生宿舍一组团'],
        type='dormitory',
        campus='future_city',
        latitude=30.455601,
        longitude=114.616756,
        description='高德地图公开 POI：中国地质大学未来城校区学生宿舍一组团。',
        address='左庙路与科技五路交叉口东220米',
        tags=['商务住宅', '住宅区', '宿舍'],
    ),
    CampusLocation(
        id='amap-poi-09',
        name='中国地质大学未来城校区学生宿舍一组团',
        aliases=['中国地质大学未来城校区学生宿舍一组团'],
        type='dormitory',
        campus='future_city',
        latitude=30.455601,
        longitude=114.616756,
        description='高德地图公开 POI：中国地质大学未来城校区学生宿舍一组团。',
        address='左庙路与科技五路交叉口东220米',
        tags=['商务住宅', '住宅区', '宿舍'],
    ),
    CampusLocation(
        id='amap-poi-10',
        name='中国地质大学未来城校区图书馆',
        aliases=['中国地质大学未来城校区图书馆'],
        type='library',
        campus='future_city',
        latitude=30.456304,
        longitude=114.618256,
        description='高德地图公开 POI：中国地质大学未来城校区图书馆。',
        address='锦程街68号中国地质大学未来城校区',
        tags=['科教文化服务', '图书馆', '图书馆'],
    ),
    CampusLocation(
        id='amap-poi-11',
        name='中国地质大学未来城校区学生活动中心',
        aliases=['中国地质大学未来城校区学生活动中心'],
        type='office',
        campus='future_city',
        latitude=30.456465,
        longitude=114.619911,
        description='高德地图公开 POI：中国地质大学未来城校区学生活动中心。',
        address='锦程街68号',
        tags=['科教文化服务', '科教文化场所', '科教文化场所'],
    ),
    CampusLocation(
        id='amap-poi-12',
        name='中国地质大学未来城校区公共教学楼1号楼',
        aliases=['中国地质大学未来城校区公共教学楼1号楼', '中国地质大学未来城校区公共教学楼'],
        type='teaching_building',
        campus='future_city',
        latitude=30.457875,
        longitude=114.618975,
        description='高德地图公开 POI：中国地质大学未来城校区公共教学楼。',
        address='锦程街与快岭东路交叉口西南400米',
        tags=['科教文化服务', '学校', '学校'],
    ),
    CampusLocation(
        id='amap-poi-13',
        name='中国地质大学未来城校区操场',
        aliases=['中国地质大学未来城校区操场'],
        type='sports',
        campus='future_city',
        latitude=30.459311,
        longitude=114.621384,
        description='高德地图公开 POI：中国地质大学未来城校区操场。',
        address='东湖新技术开发区锦程街68号中国地质大学未来城校区',
        tags=['体育休闲服务', '运动场馆', '运动场所'],
    ),
    CampusLocation(
        id='amap-poi-14',
        name='中国地质大学(武汉未来城校区)-游泳馆',
        aliases=['中国地质大学(武汉未来城校区)-游泳馆'],
        type='sports',
        campus='future_city',
        latitude=30.457633,
        longitude=114.621777,
        description='高德地图公开 POI：中国地质大学(武汉未来城校区)-游泳馆。',
        address='中国地质大学武汉未来城校区',
        tags=['体育休闲服务', '运动场馆', '游泳馆'],
    ),
    CampusLocation(
        id='amap-poi-15',
        name='中国地质大学未来城校区教工活动中心',
        aliases=['中国地质大学未来城校区教工活动中心'],
        type='office',
        campus='future_city',
        latitude=30.457121,
        longitude=114.621003,
        description='高德地图公开 POI：中国地质大学未来城校区教工活动中心。',
        address='锦程街68号',
        tags=['科教文化服务', '科教文化场所', '科教文化场所'],
    ),
    CampusLocation(
        id='amap-poi-16',
        name='中国地质大学未来城校区计算机学院',
        aliases=['中国地质大学未来城校区计算机学院'],
        type='office',
        campus='future_city',
        latitude=30.459594,
        longitude=114.618765,
        description='高德地图公开 POI：中国地质大学未来城校区计算机学院。',
        address='东湖新技术开发区锦程街68号中国地质大学未来城校区',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-17',
        name='中国地质大学西区弘毅堂',
        aliases=['中国地质大学西区弘毅堂'],
        type='office',
        campus='nanwangshan',
        latitude=30.520548,
        longitude=114.397238,
        description='高德地图公开 POI：中国地质大学西区弘毅堂。',
        address='鲁磨路388号中国地质大学南区',
        tags=['科教文化服务', '学校', '学校'],
    ),
    CampusLocation(
        id='amap-poi-18',
        name='中国地质大学西区足球场',
        aliases=['中国地质大学西区足球场'],
        type='sports',
        campus='nanwangshan',
        latitude=30.519769,
        longitude=114.39828,
        description='高德地图公开 POI：中国地质大学西区足球场。',
        address='鲁磨路485号中国地质大学西区内',
        tags=['体育休闲服务', '运动场馆', '足球场'],
    ),
    CampusLocation(
        id='amap-poi-19',
        name='中国地质大学大学生活动中心',
        aliases=['中国地质大学大学生活动中心'],
        type='office',
        campus='nanwangshan',
        latitude=30.521158,
        longitude=114.397486,
        description='高德地图公开 POI：中国地质大学大学生活动中心。',
        address='鲁磨路388号中国地质大学西区',
        tags=['科教文化服务', '学校', '学校'],
    ),
    CampusLocation(
        id='amap-poi-20',
        name='中国地质大学工程实验大楼',
        aliases=['中国地质大学工程实验大楼'],
        type='lab',
        campus='nanwangshan',
        latitude=30.523637,
        longitude=114.398222,
        description='高德地图公开 POI：中国地质大学工程实验大楼。',
        address='弘毅路与紫薇路交叉口北100米',
        tags=['科教文化服务', '学校', '学校'],
    ),
    CampusLocation(
        id='amap-poi-21',
        name='中国地质大学机械与电子信息学院',
        aliases=['中国地质大学机械与电子信息学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.523273,
        longitude=114.398296,
        description='高德地图公开 POI：中国地质大学机械与电子信息学院。',
        address='中国地质大学教二楼',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-22',
        name='中国地质大学(武汉)地质工程试验教学中心',
        aliases=['中国地质大学(武汉)地质工程试验教学中心'],
        type='other',
        campus='nanwangshan',
        latitude=30.524234,
        longitude=114.39813,
        description='高德地图公开 POI：中国地质大学(武汉)地质工程试验教学中心。',
        address='弘毅路中国地质大学(西区)',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-23',
        name='西苑美食广场(中国地质大学武汉店)',
        aliases=['西苑美食广场(中国地质大学武汉店)'],
        type='canteen',
        campus='nanwangshan',
        latitude=30.521186,
        longitude=114.396517,
        description='高德地图公开 POI：西苑美食广场(中国地质大学武汉店)。',
        address='桃李路与荟萃路交叉口南150米',
        tags=['餐饮服务', '中餐厅', '中餐厅'],
    ),
    CampusLocation(
        id='amap-poi-24',
        name='中国地质大学西区图书馆',
        aliases=['中国地质大学西区图书馆'],
        type='library',
        campus='nanwangshan',
        latitude=30.518583,
        longitude=114.399349,
        description='高德地图公开 POI：中国地质大学西区图书馆。',
        address='鲁磨路388号中国地质大学西区',
        tags=['科教文化服务', '图书馆', '图书馆'],
    ),
    CampusLocation(
        id='amap-poi-25',
        name='中国地质大学地球物理与空间信息学院',
        aliases=['中国地质大学地球物理与空间信息学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.519287,
        longitude=114.399519,
        description='高德地图公开 POI：中国地质大学地球物理与空间信息学院。',
        address='鲁磨路485中国地质大学西区',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-26',
        name='大地宝藏地质文化科普研学中心',
        aliases=['大地宝藏地质文化科普研学中心'],
        type='other',
        campus='nanwangshan',
        latitude=30.517869,
        longitude=114.40067,
        description='高德地图公开 POI：大地宝藏地质文化科普研学中心。',
        address='鲁磨路388号中国地质大学逸夫博物馆1层',
        tags=['科教文化服务', '科教文化场所', '科教文化场所'],
    ),
    CampusLocation(
        id='amap-poi-27',
        name='中国地质大学工程学院',
        aliases=['中国地质大学工程学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.519379,
        longitude=114.400637,
        description='高德地图公开 POI：中国地质大学工程学院。',
        address='鲁磨路388号',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-28',
        name='中国地质大学资源学院',
        aliases=['中国地质大学资源学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.520969,
        longitude=114.399957,
        description='高德地图公开 POI：中国地质大学资源学院。',
        address='鲁磨路485号中国地质大学西区',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-29',
        name='中国地质大学西区地球科学学院',
        aliases=['中国地质大学西区地球科学学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.521775,
        longitude=114.400125,
        description='高德地图公开 POI：中国地质大学西区地球科学学院。',
        address='鲁磨路485中国地质大学西区',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-30',
        name='中国地质大学网络中心',
        aliases=['中国地质大学网络中心'],
        type='office',
        campus='nanwangshan',
        latitude=30.520853,
        longitude=114.401114,
        description='高德地图公开 POI：中国地质大学网络中心。',
        address='中国地质大学内',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-31',
        name='中国地质大学基建处',
        aliases=['中国地质大学基建处'],
        type='office',
        campus='nanwangshan',
        latitude=30.52017,
        longitude=114.403642,
        description='高德地图公开 POI：中国地质大学基建处。',
        address='鲁磨路388号中国地质大学',
        tags=['科教文化服务', '学校', '高等院校|生活服务'],
    ),
    CampusLocation(
        id='amap-poi-32',
        name='中国地质大学游泳馆',
        aliases=['中国地质大学游泳馆'],
        type='sports',
        campus='nanwangshan',
        latitude=30.519656,
        longitude=114.402101,
        description='高德地图公开 POI：中国地质大学游泳馆。',
        address='鲁磨路388号',
        tags=['体育休闲服务', '运动场馆', '游泳馆'],
    ),
    CampusLocation(
        id='amap-poi-33',
        name='中国地质大学(东区)',
        aliases=['中国地质大学(东区)'],
        type='other',
        campus='nanwangshan',
        latitude=30.519138,
        longitude=114.404432,
        description='高德地图公开 POI：中国地质大学(东区)。',
        address='鲁磨路388号',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-34',
        name='中国地质大学(武汉)校史馆',
        aliases=['中国地质大学(武汉)校史馆'],
        type='other',
        campus='nanwangshan',
        latitude=30.518103,
        longitude=114.403966,
        description='高德地图公开 POI：中国地质大学(武汉)校史馆。',
        address='石林东路与石林南路交叉口南60米',
        tags=['科教文化服务', '科教文化场所', '科教文化场所'],
    ),
    CampusLocation(
        id='amap-poi-35',
        name='中国地质大学震旦园',
        aliases=['中国地质大学震旦园'],
        type='canteen',
        campus='nanwangshan',
        latitude=30.518328,
        longitude=114.405759,
        description='高德地图公开 POI：中国地质大学震旦园。',
        address='鲁磨路394号中国地质大学东区',
        tags=['餐饮服务', '中餐厅', '中餐厅'],
    ),
    CampusLocation(
        id='amap-poi-36',
        name='中国地质大学迎宾楼',
        aliases=['中国地质大学迎宾楼'],
        type='office',
        campus='nanwangshan',
        latitude=30.517287,
        longitude=114.405422,
        description='高德地图公开 POI：中国地质大学迎宾楼。',
        address='鲁磨路388中国地质大学东区',
        tags=['科教文化服务', '学校', '学校'],
    ),
    CampusLocation(
        id='amap-poi-37',
        name='中国地质大学东区樱园',
        aliases=['中国地质大学东区樱园'],
        type='other',
        campus='nanwangshan',
        latitude=30.51699,
        longitude=114.403692,
        description='高德地图公开 POI：中国地质大学东区樱园。',
        address='鲁磨路388号中国地质大学东区',
        tags=['风景名胜', '风景名胜', '风景名胜'],
    ),
    CampusLocation(
        id='amap-poi-38',
        name='中国地质大学东区(宝石和宝石学杂社)',
        aliases=['中国地质大学东区(宝石和宝石学杂社)'],
        type='other',
        campus='nanwangshan',
        latitude=30.516653,
        longitude=114.401848,
        description='高德地图公开 POI：中国地质大学东区(宝石和宝石学杂社)。',
        address='鲁磨路388号中国地质大学(东区)',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-39',
        name='中国地质大学东区丝绸之路学院',
        aliases=['中国地质大学东区丝绸之路学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.519311,
        longitude=114.40687,
        description='高德地图公开 POI：中国地质大学东区丝绸之路学院。',
        address='中国地质大学东区留学生大楼内',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-40',
        name='中国地质大学北区外国语学院',
        aliases=['中国地质大学北区外国语学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.527823,
        longitude=114.400035,
        description='高德地图公开 POI：中国地质大学北区外国语学院。',
        address='鲁磨路388号中国地质大学北区',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-41',
        name='中国地质大学北区公共管理学院',
        aliases=['中国地质大学北区公共管理学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.52831,
        longitude=114.400035,
        description='高德地图公开 POI：中国地质大学北区公共管理学院。',
        address='中国地质大学北二楼',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-42',
        name='中国地质大学出版社',
        aliases=['中国地质大学出版社'],
        type='office',
        campus='nanwangshan',
        latitude=30.528964,
        longitude=114.400452,
        description='高德地图公开 POI：中国地质大学出版社。',
        address='鲁磨路388号中国地质大学',
        tags=['科教文化服务', '传媒机构', '出版社'],
    ),
    CampusLocation(
        id='amap-poi-43',
        name='中国地质大学武汉环境学院大气科学系',
        aliases=['中国地质大学武汉环境学院大气科学系'],
        type='lab',
        campus='nanwangshan',
        latitude=30.528971,
        longitude=114.401532,
        description='高德地图公开 POI：中国地质大学武汉环境学院大气科学系。',
        address='北四路与致远路交叉口南60米',
        tags=['科教文化服务', '学校', '高等院校'],
    ),
    CampusLocation(
        id='amap-poi-44',
        name='中国地质大学北区综合楼',
        aliases=['中国地质大学北区综合楼'],
        type='office',
        campus='nanwangshan',
        latitude=30.529811,
        longitude=114.400519,
        description='高德地图公开 POI：中国地质大学北区综合楼。',
        address='鲁磨路388号中国地质大学北区',
        tags=['科教文化服务', '学校', '学校'],
    ),
    CampusLocation(
        id='amap-poi-45',
        name='中国地质大学北区艺术与传媒学院',
        aliases=['中国地质大学北区艺术与传媒学院'],
        type='office',
        campus='nanwangshan',
        latitude=30.530064,
        longitude=114.40163,
        description='高德地图公开 POI：中国地质大学北区艺术与传媒学院。',
        address='鲁磨路388号中国地质大学北区',
        tags=['科教文化服务', '学校', '学校'],
    ),
    CampusLocation(
        id='amap-poi-46',
        name='中国地质大学北区梅园',
        aliases=['中国地质大学北区梅园'],
        type='other',
        campus='nanwangshan',
        latitude=30.52726,
        longitude=114.40081,
        description='高德地图公开 POI：中国地质大学北区梅园。',
        address='鲁磨路364号',
        tags=['风景名胜', '风景名胜相关', '旅游景点'],
    ),
]


TYPE_KEYWORDS = {'teaching_building': ['教学楼', '上课', '教室', '课程', '公共教学楼'], 'library': ['图书', '借书', '自习', '学习'], 'canteen': ['吃饭', '食堂', '餐厅', '饭', '美食'], 'dormitory': ['宿舍', '寝室', '公寓', '组团'], 'gate': ['校门', '门口', '入口', '出入口'], 'sports': ['运动', '体育', '健身', '球馆', '操场', '游泳'], 'office': ['学院', '行政', '办公', '办事', '证明', '活动中心'], 'lab': ['实验', '实验室', '科研', '工研院', '研究院'], 'other': ['其他', '活动', '广场', '园']}


def build_map_url(location: CampusLocation, start: CampusLocation | None = None, show_route: bool = False) -> str:
    url = f"/campus-map?location={quote(location.id)}"
    if start:
        url += f"&from={quote(start.id)}"
    if show_route:
        url += "&route=1"
    return url


def list_campus_locations() -> list[dict]:
    return [location.to_dict() for location in CAMPUS_LOCATIONS]


def get_campus_location(location_id: str) -> dict | None:
    for location in CAMPUS_LOCATIONS:
        if location.id == location_id:
            return location.to_dict()
    return None


def _score_location(location: CampusLocation, keyword: str) -> int:
    normalized = keyword.strip().lower()
    if not normalized:
        return 0
    score = 0
    haystacks = [(location.name, 10), *[(alias, 8) for alias in location.aliases], *[(tag, 6) for tag in location.tags], (location.type, 5), *[(word, 5) for word in TYPE_KEYWORDS.get(location.type, [])], (location.description, 2), (location.address, 2)]
    for value, weight in haystacks:
        if normalized == value.lower():
            score += weight * 3
        elif normalized in value.lower() or value.lower() in normalized:
            score += weight
    return score


def search_campus_locations(keyword: str, limit: int = 10) -> list[dict]:
    scored = [(score, index, location) for index, location in enumerate(CAMPUS_LOCATIONS) if (score := _score_location(location, keyword)) > 0]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [location.to_dict() for _, _, location in scored[:limit]]


def find_best_location(keyword: str) -> CampusLocation | None:
    results = search_campus_locations(keyword, limit=1)
    if not results:
        return None
    location_id = results[0]["id"]
    return next((item for item in CAMPUS_LOCATIONS if item.id == location_id), None)
