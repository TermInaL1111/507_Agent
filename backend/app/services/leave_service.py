"""请假条 Word 文档生成服务。

两种类型：
- course_leave: 课程请假（交给任课老师 / 学工组备案）
- long_leave: 长假期请假（中国地质大学计算机学院长期请假手续单）
"""

import io
from datetime import date

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

from app.schemas.leave import CourseLeaveRequest, LongLeaveRequest

_FONT_NAME = "宋体"
_FONT_NAME_ASCII = "Times New Roman"
_TODAY = date.today().strftime("%Y年%m月%d日")


def _set_cell_font(cell, text: str, size: Pt = Pt(11), bold: bool = False):
    """设置单元格文字。"""
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.size = size
    run.font.name = _FONT_NAME
    run._element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)
    run.bold = bold


def _set_run_font(run, size: Pt = Pt(12), bold: bool = False):
    run.font.size = size
    run.font.name = _FONT_NAME
    run._element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)
    run.bold = bold


def _add_paragraph(doc, text: str, size: Pt = Pt(12), bold: bool = False,
                   alignment=WD_ALIGN_PARAGRAPH.LEFT, space_after: Pt = Pt(6)):
    p = doc.add_paragraph()
    p.alignment = alignment
    p.paragraph_format.space_after = space_after
    run = p.add_run(text)
    _set_run_font(run, size, bold)
    return p


def _add_underline_line(doc, label: str, value: str, size: Pt = Pt(12)):
    """带下划线的字段行，格式: label______value______"""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(label)
    _set_run_font(run, size)
    run = p.add_run(value if value else "________")
    _set_run_font(run, size)
    run.underline = True
    return p


def generate_course_leave(req: CourseLeaveRequest) -> io.BytesIO:
    """生成课程请假条 Word 文档。

    模板:
        学 生 请 假 条（交给任课老师 / 学工组备案）
        尊敬的 XX 老师：  (仅 teacher 类型)
        XX学院学工组：    (仅 student_affairs 类型)
        我是 XX班学生 XX（学号：XX），因 XX，
        请假 XX（时间），从 X年X月X日X时至 X年X月X日X时。
        本人已经将请假事宜及时告知家长...
        本人联系方式：XX  家长联系方式：XX
        本人签名：XX
        X年X月X日
        （student_affairs 类型额外）：该生情况属实，是否准假以任课老师意见为准。
    """
    doc = Document()

    # 页边距
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3)
        section.right_margin = Cm(3)

    # 标题
    title = "学 生 请 假 条（交给任课老师）" if req.recipient_type == "teacher" else "学 生 请 假 条（学工组备案）"
    _add_paragraph(doc, title, Pt(16), bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(16))

    # 称呼
    if req.recipient_type == "teacher":
        teacher = req.teacher_name or "________"
        _add_paragraph(doc, f"尊敬的 {teacher} 老师：", Pt(12), space_after=Pt(8))
    else:
        _add_paragraph(doc, "计算机学院学工组：", Pt(12), space_after=Pt(8))

    # 正文：我是 XX班学生 XX（学号：XX），因 XX，请假 XX（时间），从 X年X月X日X时至 X年X月X日X时。
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Cm(0.7)

    parts = [
        ("我 是 ", False),
        (f"{req.class_name or '____'}班", True),
        ("学生 ", False),
        (f"{req.student_name or '____'} ", True),
        ("（学号：", False),
        (f"{req.student_id or '________'} ", True),
        ("），因 ", False),
        (f"{req.reason or '________________'}，", True),
        ("请假 ", False),
        (f"{req.duration_days or '____'} ", True),
        ("（时间），从 ", False),
        (f"{req.start_date or '____年__月__日'}{req.start_time or '__'}时 ", True),
        ("至 ", False),
        (f"{req.end_date or '____年__月__日'}{req.end_time or '__'}时。", True),
    ]
    for text, underline in parts:
        run = p.add_run(text)
        _set_run_font(run, Pt(12))
        if underline:
            run.underline = True

    # 承诺语
    _add_paragraph(doc, "本人已经将请假事宜及时告知家长，且本人承诺请假期间注意安全，若有安全事故发生，个人按照学校有关管理规定承担相应责任。", Pt(12))
    _add_paragraph(doc, "特此请假。", Pt(12))

    # 联系方式
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(f"本人联系方式：{req.student_phone or '____________'}  ")
    _set_run_font(run, Pt(12))
    run = p.add_run(f"家长联系方式：{req.parent_phone or '____________'}")
    _set_run_font(run, Pt(12))

    # 签名
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(f"本人签名：{req.signature or '____________'}")
    _set_run_font(run, Pt(12))

    # 日期
    _add_paragraph(doc, req.sign_date or _TODAY, Pt(12))

    # 学工组备案额外行
    if req.recipient_type == "student_affairs":
        doc.add_paragraph()
        _add_paragraph(doc, "该生情况属实，是否准假以任课老师意见为准。", Pt(11))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def generate_long_leave(req: LongLeaveRequest) -> io.BytesIO:
    """生成长假期请假手续单 Word 文档。

    模板: 中国地质大学计算机学院2023级长期请假手续单（表格格式）
    """
    doc = Document()

    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(1.5)
        section.right_margin = Cm(1.5)

    # 标题
    _add_paragraph(doc, "中国地质大学计算机学院2023级长期请假手续单",
                   Pt(14), bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(14))

    # ── 信息表格 ──
    table = doc.add_table(rows=7, cols=4, style="Table Grid")
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # 合并请假时间行 (row 4, 后3列)
    table.cell(4, 1).merge(table.cell(4, 3))
    # 合并请假原因区域 (row 5, 4列)
    table.cell(5, 0).merge(table.cell(5, 3))

    rows_data = [
        # (label_col0, val_col1, label_col2, val_col3)
        ("姓 名", req.student_name, "学 号", req.student_id),
        ("班 号", req.class_name, "本人离校期间电话", req.phone),
        ("亲属关系", req.parent_relation, "亲属联系电话", req.parent_phone),
        ("请假时间", f"{req.leave_start or '____年__月__日__时'}(离校) --- {req.leave_end or '____年__月__日__时'}(返校) 共 {req.total_days or '__'} 天", "", ""),
        # row 5 merged → 请假原因 + 去向
    ]

    for r, (l0, v0, l2, v2) in enumerate(rows_data):
        if r == 4:  # 请假时间行 — 4列，后3列已合并
            _set_cell_font(table.cell(r, 0), l0, Pt(10.5), bold=True)
            _set_cell_font(table.cell(r, 1), v0, Pt(10.5))
        elif r < 5:
            _set_cell_font(table.cell(r, 0), l0, Pt(10.5), bold=True)
            _set_cell_font(table.cell(r, 1), v0, Pt(10.5))
            _set_cell_font(table.cell(r, 2), l2, Pt(10.5), bold=True)
            _set_cell_font(table.cell(r, 3), v2, Pt(10.5))

    # 请假原因 + 去向 (row 5, merged)
    cell_reason = table.cell(5, 0)
    cell_reason.text = ""
    reason_text = f"1. 请假原因：\n{req.reason or '________________'}\n\n2、请假去向详细地址：\n{req.destination or '________________'}"
    p = cell_reason.paragraphs[0]
    for i, line in enumerate(reason_text.split("\n")):
        if i > 0:
            p = cell_reason.add_paragraph()
        run = p.add_run(line)
        run.font.size = Pt(10.5)
        run.font.name = _FONT_NAME
        run._element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)

    # 承诺语 (row 6)
    pledge_cell = table.cell(6, 0)
    table.cell(6, 0).merge(table.cell(6, 3))
    pledge_cell.text = ""
    p = pledge_cell.paragraphs[0]
    run = p.add_run("本人已经将请假事宜及时间告知家长，并会让家长短信告知辅导员已获知此事，且本人承诺请假期间做好防护，注意安全，若有安全事故发生，个人承担相应责任。望批准。")
    run.font.size = Pt(10.5)
    run.font.name = _FONT_NAME
    run._element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)

    # 签字 + 日期
    p = pledge_cell.add_paragraph()
    run = p.add_run(f"\n（本人签字）{req.signature or '____________'}")
    run.font.size = Pt(10.5)
    run.font.name = _FONT_NAME
    run._element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)

    p = pledge_cell.add_paragraph()
    run = p.add_run(f"{req.sign_date or _TODAY}")
    run.font.size = Pt(10.5)
    run.font.name = _FONT_NAME
    run._element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)

    # ── 班主任/辅导员签字表格 ──
    table2 = doc.add_table(rows=2, cols=2, style="Table Grid")
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_cell_font(table2.cell(0, 0), "班主任意见", Pt(10.5), bold=True)
    _set_cell_font(table2.cell(0, 1), "辅导员意见", Pt(10.5), bold=True)

    for col in range(2):
        cell = table2.cell(1, col)
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run("（要找班主任签字，如果班主任无法签字请假单背面附上同意截图）" if col == 0 else "（签字）")
        run.font.size = Pt(9)
        run.font.name = _FONT_NAME
        run._element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)

        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run2 = p2.add_run(f"\n（签字）\n\n年 月 日")
        run2.font.size = Pt(9)
        run2.font.name = _FONT_NAME
        run2._element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)

    # ── 销假 ──
    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run("> 学生返校销假")
    _set_run_font(run, Pt(10.5), bold=True)
    p = doc.add_paragraph()
    run = p.add_run(f"（学生签字）____________    {req.sign_date or '____年__月__日'}")
    _set_run_font(run, Pt(10.5))

    # 备注
    _add_paragraph(doc, "备注：学生请假，必须如实填写上表，经班主任和辅导员同意后，才可离校，返校后及时销假。未按要求履行请假手续外出者，按学校《学生手册》规定视情节轻重给予不同程度的违纪处分，取消评奖评优资格。", Pt(9))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def generate_leave_docx(leave_type: str, course: CourseLeaveRequest | None,
                        long_req: LongLeaveRequest | None) -> tuple[io.BytesIO, str]:
    """返回 (file_buffer, filename)。"""
    if leave_type == "course_leave":
        req = course or CourseLeaveRequest()
        buf = generate_course_leave(req)
        name = "学生请假条.docx"
    else:
        req = long_req or LongLeaveRequest()
        buf = generate_long_leave(req)
        name = "长期请假手续单.docx"
    return buf, name
