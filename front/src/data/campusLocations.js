export const campusLocationTypes = [
  { label: '全部', value: 'all' },
  { label: '教学楼', value: 'teaching' },
  { label: '食堂', value: 'canteen' },
  { label: '图书馆', value: 'library' },
  { label: '宿舍', value: 'dormitory' },
  { label: '运动场馆', value: 'sports' },
  { label: '服务', value: 'service' },
  { label: '其他', value: 'other' },
];

export const campusTypeLabels = {
  teaching: '教学楼',
  canteen: '食堂',
  library: '图书馆',
  dormitory: '宿舍',
  sports: '运动场',
  service: '教学/服务',
  other: '其他',
};

export const campusList = [
  { key: 'future_city', label: '未来城校区' },
  { key: 'nanwangshan', label: '南望山校区' },
  { key: 'all', label: '全部校区' },
];

// Same POIs as backend campus_location_service.py; used only when API is unavailable.
export const mockCampusLocations = [
  {
    "id": 1,
    "key": "amap-poi-01",
    "name": "中国地质大学未来城校区资环工研院",
    "aliases": [
      "中国地质大学未来城校区资环工研院"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "东湖新技术开发区锦程街68号中国地质大学未来城校区",
    "description": "高德地图公开 POI：中国地质大学未来城校区资环工研院。",
    "longitude": 114.612655,
    "latitude": 30.45868,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 2,
    "key": "amap-poi-02",
    "name": "武汉地质资源环境工业技术研究院园区",
    "aliases": [
      "武汉地质资源环境工业技术研究院园区"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "左庙路中国地质大学(未来城校区)",
    "description": "高德地图公开 POI：武汉地质资源环境工业技术研究院园区。",
    "longitude": 114.613325,
    "latitude": 30.458175,
    "tags": [
      "科教文化服务",
      "科教文化场所",
      "科教文化场所"
    ]
  },
  {
    "id": 3,
    "key": "amap-poi-03",
    "name": "中国地质大学未来城校区经济管理学院",
    "aliases": [
      "中国地质大学未来城校区经济管理学院"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "东湖新技术开发区锦程街68号中国地质大学未来城校区",
    "description": "高德地图公开 POI：中国地质大学未来城校区经济管理学院。",
    "longitude": 114.614572,
    "latitude": 30.458548,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 4,
    "key": "amap-poi-04",
    "name": "中国地质大学未来城校区材料与化学学院",
    "aliases": [
      "中国地质大学未来城校区材料与化学学院"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "东湖新技术开发区锦程街68号中国地质大学未来城校区",
    "description": "高德地图公开 POI：中国地质大学未来城校区材料与化学学院。",
    "longitude": 114.616211,
    "latitude": 30.45843,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 5,
    "key": "amap-poi-05",
    "name": "中国地质大学未来城校区环境学院",
    "aliases": [
      "中国地质大学未来城校区环境学院"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "东湖新技术开发区左岭锦程街68号",
    "description": "高德地图公开 POI：中国地质大学未来城校区环境学院。",
    "longitude": 114.615565,
    "latitude": 30.457458,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 6,
    "key": "amap-poi-06",
    "name": "中国地质大学未来城校区生物地质与环境地质国家重点实验室",
    "aliases": [
      "中国地质大学未来城校区生物地质与环境地质国家重点实验室"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "湖北省武汉市洪山区左庙路",
    "description": "高德地图公开 POI：中国地质大学未来城校区生物地质与环境地质国家重点实验室。",
    "longitude": 114.617385,
    "latitude": 30.457879,
    "tags": [
      "科教文化服务",
      "科教文化场所",
      "科教文化场所"
    ]
  },
  {
    "id": 7,
    "key": "amap-poi-07",
    "name": "中国地质大学(武汉)未来城-地球广场",
    "aliases": [
      "中国地质大学(武汉)未来城-地球广场"
    ],
    "type": "other",
    "campus": "future_city",
    "address": "左庙路中国地质大学(未来城校区)",
    "description": "高德地图公开 POI：中国地质大学(武汉)未来城-地球广场。",
    "longitude": 114.616758,
    "latitude": 30.45639,
    "tags": [
      "风景名胜",
      "公园广场",
      "城市广场"
    ]
  },
  {
    "id": 8,
    "key": "amap-poi-08",
    "name": "中国地质大学未来城校区学生宿舍一组团3栋",
    "aliases": [
      "中国地质大学未来城校区学生宿舍一组团3栋",
      "中国地质大学未来城校区学生宿舍一组团"
    ],
    "type": "dormitory",
    "campus": "future_city",
    "address": "左庙路与科技五路交叉口东220米",
    "description": "高德地图公开 POI：中国地质大学未来城校区学生宿舍一组团。",
    "longitude": 114.616756,
    "latitude": 30.455601,
    "tags": [
      "商务住宅",
      "住宅区",
      "宿舍"
    ]
  },
  {
    "id": 9,
    "key": "amap-poi-09",
    "name": "中国地质大学未来城校区学生宿舍一组团",
    "aliases": [
      "中国地质大学未来城校区学生宿舍一组团"
    ],
    "type": "dormitory",
    "campus": "future_city",
    "address": "左庙路与科技五路交叉口东220米",
    "description": "高德地图公开 POI：中国地质大学未来城校区学生宿舍一组团。",
    "longitude": 114.616756,
    "latitude": 30.455601,
    "tags": [
      "商务住宅",
      "住宅区",
      "宿舍"
    ]
  },
  {
    "id": 10,
    "key": "amap-poi-10",
    "name": "中国地质大学未来城校区图书馆",
    "aliases": [
      "中国地质大学未来城校区图书馆"
    ],
    "type": "library",
    "campus": "future_city",
    "address": "锦程街68号中国地质大学未来城校区",
    "description": "高德地图公开 POI：中国地质大学未来城校区图书馆。",
    "longitude": 114.618256,
    "latitude": 30.456304,
    "tags": [
      "科教文化服务",
      "图书馆",
      "图书馆"
    ]
  },
  {
    "id": 11,
    "key": "amap-poi-11",
    "name": "中国地质大学未来城校区学生活动中心",
    "aliases": [
      "中国地质大学未来城校区学生活动中心"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "锦程街68号",
    "description": "高德地图公开 POI：中国地质大学未来城校区学生活动中心。",
    "longitude": 114.619911,
    "latitude": 30.456465,
    "tags": [
      "科教文化服务",
      "科教文化场所",
      "科教文化场所"
    ]
  },
  {
    "id": 12,
    "key": "amap-poi-12",
    "name": "中国地质大学未来城校区公共教学楼1号楼",
    "aliases": [
      "中国地质大学未来城校区公共教学楼1号楼",
      "中国地质大学未来城校区公共教学楼"
    ],
    "type": "teaching",
    "campus": "future_city",
    "address": "锦程街与快岭东路交叉口西南400米",
    "description": "高德地图公开 POI：中国地质大学未来城校区公共教学楼。",
    "longitude": 114.618975,
    "latitude": 30.457875,
    "tags": [
      "科教文化服务",
      "学校",
      "学校"
    ]
  },
  {
    "id": 13,
    "key": "amap-poi-13",
    "name": "中国地质大学未来城校区操场",
    "aliases": [
      "中国地质大学未来城校区操场"
    ],
    "type": "sports",
    "campus": "future_city",
    "address": "东湖新技术开发区锦程街68号中国地质大学未来城校区",
    "description": "高德地图公开 POI：中国地质大学未来城校区操场。",
    "longitude": 114.621384,
    "latitude": 30.459311,
    "tags": [
      "体育休闲服务",
      "运动场馆",
      "运动场所"
    ]
  },
  {
    "id": 14,
    "key": "amap-poi-14",
    "name": "中国地质大学(武汉未来城校区)-游泳馆",
    "aliases": [
      "中国地质大学(武汉未来城校区)-游泳馆"
    ],
    "type": "sports",
    "campus": "future_city",
    "address": "中国地质大学武汉未来城校区",
    "description": "高德地图公开 POI：中国地质大学(武汉未来城校区)-游泳馆。",
    "longitude": 114.621777,
    "latitude": 30.457633,
    "tags": [
      "体育休闲服务",
      "运动场馆",
      "游泳馆"
    ]
  },
  {
    "id": 15,
    "key": "amap-poi-15",
    "name": "中国地质大学未来城校区教工活动中心",
    "aliases": [
      "中国地质大学未来城校区教工活动中心"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "锦程街68号",
    "description": "高德地图公开 POI：中国地质大学未来城校区教工活动中心。",
    "longitude": 114.621003,
    "latitude": 30.457121,
    "tags": [
      "科教文化服务",
      "科教文化场所",
      "科教文化场所"
    ]
  },
  {
    "id": 16,
    "key": "amap-poi-16",
    "name": "中国地质大学未来城校区计算机学院",
    "aliases": [
      "中国地质大学未来城校区计算机学院"
    ],
    "type": "service",
    "campus": "future_city",
    "address": "东湖新技术开发区锦程街68号中国地质大学未来城校区",
    "description": "高德地图公开 POI：中国地质大学未来城校区计算机学院。",
    "longitude": 114.618765,
    "latitude": 30.459594,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 17,
    "key": "amap-poi-17",
    "name": "中国地质大学西区弘毅堂",
    "aliases": [
      "中国地质大学西区弘毅堂"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学南区",
    "description": "高德地图公开 POI：中国地质大学西区弘毅堂。",
    "longitude": 114.397238,
    "latitude": 30.520548,
    "tags": [
      "科教文化服务",
      "学校",
      "学校"
    ]
  },
  {
    "id": 18,
    "key": "amap-poi-18",
    "name": "中国地质大学西区足球场",
    "aliases": [
      "中国地质大学西区足球场"
    ],
    "type": "sports",
    "campus": "nanwangshan",
    "address": "鲁磨路485号中国地质大学西区内",
    "description": "高德地图公开 POI：中国地质大学西区足球场。",
    "longitude": 114.39828,
    "latitude": 30.519769,
    "tags": [
      "体育休闲服务",
      "运动场馆",
      "足球场"
    ]
  },
  {
    "id": 19,
    "key": "amap-poi-19",
    "name": "中国地质大学大学生活动中心",
    "aliases": [
      "中国地质大学大学生活动中心"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学西区",
    "description": "高德地图公开 POI：中国地质大学大学生活动中心。",
    "longitude": 114.397486,
    "latitude": 30.521158,
    "tags": [
      "科教文化服务",
      "学校",
      "学校"
    ]
  },
  {
    "id": 20,
    "key": "amap-poi-20",
    "name": "中国地质大学工程实验大楼",
    "aliases": [
      "中国地质大学工程实验大楼"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "弘毅路与紫薇路交叉口北100米",
    "description": "高德地图公开 POI：中国地质大学工程实验大楼。",
    "longitude": 114.398222,
    "latitude": 30.523637,
    "tags": [
      "科教文化服务",
      "学校",
      "学校"
    ]
  },
  {
    "id": 21,
    "key": "amap-poi-21",
    "name": "中国地质大学机械与电子信息学院",
    "aliases": [
      "中国地质大学机械与电子信息学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "中国地质大学教二楼",
    "description": "高德地图公开 POI：中国地质大学机械与电子信息学院。",
    "longitude": 114.398296,
    "latitude": 30.523273,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 22,
    "key": "amap-poi-22",
    "name": "中国地质大学(武汉)地质工程试验教学中心",
    "aliases": [
      "中国地质大学(武汉)地质工程试验教学中心"
    ],
    "type": "other",
    "campus": "nanwangshan",
    "address": "弘毅路中国地质大学(西区)",
    "description": "高德地图公开 POI：中国地质大学(武汉)地质工程试验教学中心。",
    "longitude": 114.39813,
    "latitude": 30.524234,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 23,
    "key": "amap-poi-23",
    "name": "西苑美食广场(中国地质大学武汉店)",
    "aliases": [
      "西苑美食广场(中国地质大学武汉店)"
    ],
    "type": "canteen",
    "campus": "nanwangshan",
    "address": "桃李路与荟萃路交叉口南150米",
    "description": "高德地图公开 POI：西苑美食广场(中国地质大学武汉店)。",
    "longitude": 114.396517,
    "latitude": 30.521186,
    "tags": [
      "餐饮服务",
      "中餐厅",
      "中餐厅"
    ]
  },
  {
    "id": 24,
    "key": "amap-poi-24",
    "name": "中国地质大学西区图书馆",
    "aliases": [
      "中国地质大学西区图书馆"
    ],
    "type": "library",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学西区",
    "description": "高德地图公开 POI：中国地质大学西区图书馆。",
    "longitude": 114.399349,
    "latitude": 30.518583,
    "tags": [
      "科教文化服务",
      "图书馆",
      "图书馆"
    ]
  },
  {
    "id": 25,
    "key": "amap-poi-25",
    "name": "中国地质大学地球物理与空间信息学院",
    "aliases": [
      "中国地质大学地球物理与空间信息学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路485中国地质大学西区",
    "description": "高德地图公开 POI：中国地质大学地球物理与空间信息学院。",
    "longitude": 114.399519,
    "latitude": 30.519287,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 26,
    "key": "amap-poi-26",
    "name": "大地宝藏地质文化科普研学中心",
    "aliases": [
      "大地宝藏地质文化科普研学中心"
    ],
    "type": "other",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学逸夫博物馆1层",
    "description": "高德地图公开 POI：大地宝藏地质文化科普研学中心。",
    "longitude": 114.40067,
    "latitude": 30.517869,
    "tags": [
      "科教文化服务",
      "科教文化场所",
      "科教文化场所"
    ]
  },
  {
    "id": 27,
    "key": "amap-poi-27",
    "name": "中国地质大学工程学院",
    "aliases": [
      "中国地质大学工程学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388号",
    "description": "高德地图公开 POI：中国地质大学工程学院。",
    "longitude": 114.400637,
    "latitude": 30.519379,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 28,
    "key": "amap-poi-28",
    "name": "中国地质大学资源学院",
    "aliases": [
      "中国地质大学资源学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路485号中国地质大学西区",
    "description": "高德地图公开 POI：中国地质大学资源学院。",
    "longitude": 114.399957,
    "latitude": 30.520969,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 29,
    "key": "amap-poi-29",
    "name": "中国地质大学西区地球科学学院",
    "aliases": [
      "中国地质大学西区地球科学学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路485中国地质大学西区",
    "description": "高德地图公开 POI：中国地质大学西区地球科学学院。",
    "longitude": 114.400125,
    "latitude": 30.521775,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 30,
    "key": "amap-poi-30",
    "name": "中国地质大学网络中心",
    "aliases": [
      "中国地质大学网络中心"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "中国地质大学内",
    "description": "高德地图公开 POI：中国地质大学网络中心。",
    "longitude": 114.401114,
    "latitude": 30.520853,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 31,
    "key": "amap-poi-31",
    "name": "中国地质大学基建处",
    "aliases": [
      "中国地质大学基建处"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学",
    "description": "高德地图公开 POI：中国地质大学基建处。",
    "longitude": 114.403642,
    "latitude": 30.52017,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校|生活服务"
    ]
  },
  {
    "id": 32,
    "key": "amap-poi-32",
    "name": "中国地质大学游泳馆",
    "aliases": [
      "中国地质大学游泳馆"
    ],
    "type": "sports",
    "campus": "nanwangshan",
    "address": "鲁磨路388号",
    "description": "高德地图公开 POI：中国地质大学游泳馆。",
    "longitude": 114.402101,
    "latitude": 30.519656,
    "tags": [
      "体育休闲服务",
      "运动场馆",
      "游泳馆"
    ]
  },
  {
    "id": 33,
    "key": "amap-poi-33",
    "name": "中国地质大学(东区)",
    "aliases": [
      "中国地质大学(东区)"
    ],
    "type": "other",
    "campus": "nanwangshan",
    "address": "鲁磨路388号",
    "description": "高德地图公开 POI：中国地质大学(东区)。",
    "longitude": 114.404432,
    "latitude": 30.519138,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 34,
    "key": "amap-poi-34",
    "name": "中国地质大学(武汉)校史馆",
    "aliases": [
      "中国地质大学(武汉)校史馆"
    ],
    "type": "other",
    "campus": "nanwangshan",
    "address": "石林东路与石林南路交叉口南60米",
    "description": "高德地图公开 POI：中国地质大学(武汉)校史馆。",
    "longitude": 114.403966,
    "latitude": 30.518103,
    "tags": [
      "科教文化服务",
      "科教文化场所",
      "科教文化场所"
    ]
  },
  {
    "id": 35,
    "key": "amap-poi-35",
    "name": "中国地质大学震旦园",
    "aliases": [
      "中国地质大学震旦园"
    ],
    "type": "canteen",
    "campus": "nanwangshan",
    "address": "鲁磨路394号中国地质大学东区",
    "description": "高德地图公开 POI：中国地质大学震旦园。",
    "longitude": 114.405759,
    "latitude": 30.518328,
    "tags": [
      "餐饮服务",
      "中餐厅",
      "中餐厅"
    ]
  },
  {
    "id": 36,
    "key": "amap-poi-36",
    "name": "中国地质大学迎宾楼",
    "aliases": [
      "中国地质大学迎宾楼"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388中国地质大学东区",
    "description": "高德地图公开 POI：中国地质大学迎宾楼。",
    "longitude": 114.405422,
    "latitude": 30.517287,
    "tags": [
      "科教文化服务",
      "学校",
      "学校"
    ]
  },
  {
    "id": 37,
    "key": "amap-poi-37",
    "name": "中国地质大学东区樱园",
    "aliases": [
      "中国地质大学东区樱园"
    ],
    "type": "other",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学东区",
    "description": "高德地图公开 POI：中国地质大学东区樱园。",
    "longitude": 114.403692,
    "latitude": 30.51699,
    "tags": [
      "风景名胜",
      "风景名胜",
      "风景名胜"
    ]
  },
  {
    "id": 38,
    "key": "amap-poi-38",
    "name": "中国地质大学东区(宝石和宝石学杂社)",
    "aliases": [
      "中国地质大学东区(宝石和宝石学杂社)"
    ],
    "type": "other",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学(东区)",
    "description": "高德地图公开 POI：中国地质大学东区(宝石和宝石学杂社)。",
    "longitude": 114.401848,
    "latitude": 30.516653,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 39,
    "key": "amap-poi-39",
    "name": "中国地质大学东区丝绸之路学院",
    "aliases": [
      "中国地质大学东区丝绸之路学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "中国地质大学东区留学生大楼内",
    "description": "高德地图公开 POI：中国地质大学东区丝绸之路学院。",
    "longitude": 114.40687,
    "latitude": 30.519311,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 40,
    "key": "amap-poi-40",
    "name": "中国地质大学北区外国语学院",
    "aliases": [
      "中国地质大学北区外国语学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学北区",
    "description": "高德地图公开 POI：中国地质大学北区外国语学院。",
    "longitude": 114.400035,
    "latitude": 30.527823,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 41,
    "key": "amap-poi-41",
    "name": "中国地质大学北区公共管理学院",
    "aliases": [
      "中国地质大学北区公共管理学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "中国地质大学北二楼",
    "description": "高德地图公开 POI：中国地质大学北区公共管理学院。",
    "longitude": 114.400035,
    "latitude": 30.52831,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 42,
    "key": "amap-poi-42",
    "name": "中国地质大学出版社",
    "aliases": [
      "中国地质大学出版社"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学",
    "description": "高德地图公开 POI：中国地质大学出版社。",
    "longitude": 114.400452,
    "latitude": 30.528964,
    "tags": [
      "科教文化服务",
      "传媒机构",
      "出版社"
    ]
  },
  {
    "id": 43,
    "key": "amap-poi-43",
    "name": "中国地质大学武汉环境学院大气科学系",
    "aliases": [
      "中国地质大学武汉环境学院大气科学系"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "北四路与致远路交叉口南60米",
    "description": "高德地图公开 POI：中国地质大学武汉环境学院大气科学系。",
    "longitude": 114.401532,
    "latitude": 30.528971,
    "tags": [
      "科教文化服务",
      "学校",
      "高等院校"
    ]
  },
  {
    "id": 44,
    "key": "amap-poi-44",
    "name": "中国地质大学北区综合楼",
    "aliases": [
      "中国地质大学北区综合楼"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学北区",
    "description": "高德地图公开 POI：中国地质大学北区综合楼。",
    "longitude": 114.400519,
    "latitude": 30.529811,
    "tags": [
      "科教文化服务",
      "学校",
      "学校"
    ]
  },
  {
    "id": 45,
    "key": "amap-poi-45",
    "name": "中国地质大学北区艺术与传媒学院",
    "aliases": [
      "中国地质大学北区艺术与传媒学院"
    ],
    "type": "service",
    "campus": "nanwangshan",
    "address": "鲁磨路388号中国地质大学北区",
    "description": "高德地图公开 POI：中国地质大学北区艺术与传媒学院。",
    "longitude": 114.40163,
    "latitude": 30.530064,
    "tags": [
      "科教文化服务",
      "学校",
      "学校"
    ]
  },
  {
    "id": 46,
    "key": "amap-poi-46",
    "name": "中国地质大学北区梅园",
    "aliases": [
      "中国地质大学北区梅园"
    ],
    "type": "other",
    "campus": "nanwangshan",
    "address": "鲁磨路364号",
    "description": "高德地图公开 POI：中国地质大学北区梅园。",
    "longitude": 114.40081,
    "latitude": 30.52726,
    "tags": [
      "风景名胜",
      "风景名胜相关",
      "旅游景点"
    ]
  }
];
