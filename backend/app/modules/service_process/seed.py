from sqlalchemy import select

from app.db.db_config import AsyncSessionLocal
from app.models.chat_history import ServiceProcess


SEED_PROCESSES = [
    {
        "code": "leave_application",
        "name": "请假申请",
        "category": "leave",
        "description": "引导填写请假信息，生成请假条材料，并提示按学院或辅导员要求提交。",
        "target_user": "需要办理课程、活动或事务请假的在校学生",
        "department": "所在学院/辅导员/任课教师",
        "location": "请以学院通知或学校官方系统为准",
        "contact": "请联系辅导员或对应任课教师",
        "required_materials": ["请假原因说明", "请假开始与结束时间", "课程或活动影响说明", "审批人信息", "必要证明材料"],
        "steps": ["选择请假类型", "填写请假原因", "填写开始和结束时间", "补充课程或活动影响", "填写审批人信息", "预览并确认请假条", "按学校要求提交"],
        "faq": [{"q": "系统会自动提交吗？", "a": "不会。当前仅生成材料和指引，需按学校官方要求提交。"}],
        "source_type": "seed",
        "source_id": "leave-v1",
    },
    {
        "code": "repair_request",
        "name": "宿舍 / 校园设施报修",
        "category": "repair",
        "description": "收集报修地点、设施类型和问题描述，生成报修办理清单。",
        "target_user": "遇到宿舍或校园公共设施故障的学生",
        "department": "后勤或物业服务部门",
        "location": "请以学校后勤平台或宿管通知为准",
        "contact": "请以学校后勤平台公布信息为准",
        "required_materials": ["报修地点", "设施类型", "问题描述", "图片附件（可选）", "联系方式（可选）"],
        "steps": ["填写报修地点", "选择设施类型", "描述问题", "补充图片或联系方式", "按学校后勤平台要求提交"],
        "faq": [{"q": "能直接提交后勤系统吗？", "a": "当前没有真实对接接口，只生成指引和待办提醒。"}],
        "source_type": "seed",
        "source_id": "repair-v1",
    },
    {
        "code": "certificate_application",
        "name": "在读证明 / 成绩证明申请",
        "category": "certificate",
        "description": "整理证明办理条件、材料清单和办理路径，必要时检索知识库来源。",
        "target_user": "需要办理在读证明或成绩证明的学生",
        "department": "教务部门或学院教务办",
        "location": "知识库无可靠来源时，请以学校官方系统或学院通知为准",
        "contact": "请以学校官方通知为准",
        "required_materials": ["本人身份信息", "证明用途", "申请类型", "学校要求的其他材料"],
        "steps": ["确认申请类型", "核对用途和份数", "查询官方办理入口或地点", "准备材料", "按官方要求提交"],
        "faq": [{"q": "没有查到地点怎么办？", "a": "不要猜测地点，请联系学院教务办或查看学校官方通知。"}],
        "source_type": "seed",
        "source_id": "certificate-v1",
    },
    {
        "code": "venue_booking",
        "name": "场地预约指引",
        "category": "venue",
        "description": "引导填写用途、时间、人数和设备需求，生成预约申请草稿并提醒检查课表冲突。",
        "target_user": "需要预约教室、会议室或活动场地的学生",
        "department": "场地主管部门/学院/教务或团委",
        "location": "请以学校官方预约系统或场地管理部门通知为准",
        "contact": "请以官方系统公布信息为准",
        "required_materials": ["预约用途", "预约时间", "预计人数", "设备需求", "负责人信息"],
        "steps": ["填写场地用途", "填写预约时间", "填写人数和设备需求", "检查个人日程冲突", "生成申请草稿", "按官方渠道提交"],
        "faq": [{"q": "系统会显示预约成功吗？", "a": "不会。当前只能生成申请草稿或提醒，不能替代官方预约系统。"}],
        "source_type": "seed",
        "source_id": "venue-v1",
    },
]


async def seed_service_processes() -> None:
    async with AsyncSessionLocal() as db:
        for item in SEED_PROCESSES:
            result = await db.execute(select(ServiceProcess).where(ServiceProcess.code == item["code"]))
            existing = result.scalar_one_or_none()
            if existing:
                continue
            db.add(ServiceProcess(**item, enabled=True))
        await db.commit()
