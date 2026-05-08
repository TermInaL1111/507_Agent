from pydantic import BaseModel
from typing import Optional, Literal


class CourseLeaveRequest(BaseModel):
    """课程请假（交给任课老师 / 学工组备案）"""
    recipient_type: Literal["teacher", "student_affairs"] = "teacher"
    teacher_name: str = ""          # 老师姓名，仅 teacher 类型需要
    class_name: str = ""            # 班级
    student_name: str = ""          # 姓名
    student_id: str = ""            # 学号
    reason: str = ""                # 请假原因
    duration_days: str = ""         # 请假天数
    start_date: str = ""            # 开始日期 YYYY年M月D日
    start_time: str = ""            # 开始时间 H时
    end_date: str = ""              # 结束日期 YYYY年M月D日
    end_time: str = ""              # 结束时间 H时
    student_phone: str = ""         # 本人联系方式
    parent_phone: str = ""          # 家长联系方式
    signature: str = ""             # 本人签名
    sign_date: str = ""             # 签字日期 YYYY年M月D日


class LongLeaveRequest(BaseModel):
    """长假期请假（中国地质大学计算机学院长期请假手续单）"""
    student_name: str = ""
    student_id: str = ""
    class_name: str = ""            # 班号
    phone: str = ""                 # 本人离校期间电话
    parent_relation: str = ""       # 亲属关系
    parent_phone: str = ""          # 亲属联系电话
    leave_start: str = ""           # 离校时间 e.g. "2026年5月10日8时"
    leave_end: str = ""             # 返校时间
    total_days: str = ""            # 共多少天
    reason: str = ""                # 请假原因
    destination: str = ""           # 请假去向详细地址
    signature: str = ""             # 本人签字
    sign_date: str = ""             # 签字日期


class LeaveGenerateRequest(BaseModel):
    leave_type: Literal["course_leave", "long_leave"]
    # 课程请假
    course_leave: Optional[CourseLeaveRequest] = None
    # 长假期请假
    long_leave: Optional[LongLeaveRequest] = None
