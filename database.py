#################################################################################
## database.py - low-level data sources for the Penn CIS Teaching Dashboard
##
## Access to CSV / relational tables used to maintain student progress
##
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
## 
##   http://www.apache.org/licenses/LICENSE-2.0
## 
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.    
##
#################################################################################

import yaml
import sys, traceback
import sqlite3
import pandas as pd
import sqlalchemy
from sqlalchemy.sql import text
from datetime import datetime

include_gradescope_data = True
include_canvas_data = True

with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

    if 'show' in config['canvas']:
        include_canvas_data = config['canvas']['show']
        print ('Canvas data: {}'.format(include_canvas_data))

    if 'show' in config['gradescope']:
        include_gradescope_data = config['gradescope']['show']
        print ('Gradescope data: {}'.format(include_gradescope_data))


# connection = sqlite3.connect("grades.db", check_same_thread=False)
dbEngine=sqlalchemy.create_engine('sqlite:///./dashboard.db') # ensure this is the correct path for the sqlite file. 

connection = dbEngine.connect()

def get_gs_students() -> pd.DataFrame:
    return pd.read_sql_table("gs_students", connection)

def get_canvas_students() -> pd.DataFrame:
    return pd.read_sql_table("canvas_students", connection)
    # return pd.read_csv('data/canvas_students.csv')

def get_aligned_students(include_gs: bool, include_canvas: bool) -> pd.DataFrame:
    with dbEngine.connect() as connection:
        if include_gs and include_canvas:
            # SQLite does not support full outerjoin
            students = pd.read_sql(sql=text("""select cast(sid as int) as gs_student_id, cast(student_id as int) as student_id, 
                                           case when gs.name is not null then gs.name else c.name end as student, 
                                           case when emails is not null then emails else c.email end as email, cast(user_id as int) as gs_user_id, gs.course_id as gs_course_id, lti as canvas_course_id, c.id as canvas_sid
                                           from gs_students gs join gs_courses crs on gs.course_id=crs.cid left join canvas_students c on cast(student_id as int) = cast(sis_user_id as int)
                                           where role like "%STUDENT"
                                           union
                                           select cast(null as int) as gs_student_id, cast(c.sis_user_id as int) as student_id, c.name,
                                           c.email as email, null as gs_user_id, null as gs_course_id, c.course_id as canvas_course_id, c.id as canvas_sid
                                           from canvas_students c
                                           where not exists (select * from gs_students where cast(student_id as int) = cast(c.sis_user_id as int))
                                           """), con=connection)
        elif include_gs:
            students = pd.read_sql(sql=text("""select cast(sid as int) as gs_student_id, cast(student_id as int) as student_id, gs.name as student, emails as email, cast(user_id as int) as gs_user_id, gs.course_id as gs_course_id, lti as canvas_course_id, null as canvas_sid
                                           from gs_students gs join gs_courses crs on cast(gs.course_id as int)=cast(crs.cid as int)
                                           where role like "%STUDENT"
                                           """), con=connection)
        else:
            students = pd.read_sql(sql=text("""select null as gs_student_id, cast(sis_user_id as int) as student_id,name as student, email, null as gs_user_id, null as gs_course_id, course_id as canvas_course_id, c.id as canvas_sid
                                    from canvas_students c"""), con=connection)

        return students

def get_gs_courses() -> pd.DataFrame:
    return pd.read_sql_table("gs_courses", connection)

def get_canvas_courses() -> pd.DataFrame:
    return pd.read_sql_table("canvas_courses", connection)
    # return pd.read_csv('data/canvas_courses.csv')

def get_aligned_courses(include_gs: bool, include_canvas: bool) -> pd.DataFrame:
    with dbEngine.connect() as connection:
        if include_gs and include_canvas:
            # SQLite does not support full outerjoin
            courses = pd.read_sql(sql=text("""select cid as gs_course_id, gs.name as gs_name, c.name as canvas_name, shortname, year as term, lti as canvas_course_id, sis_course_id, start_at, end_at
                                    from gs_courses gs left join canvas_courses c on gs.lti = c.id
                                           union
                                           select cid as gs_course_id, gs.name as gs_name, c.name as canvas_name, shortname, year as term, c.id as canvas_course_id, sis_course_id, start_at, end_at
                                    from  canvas_courses c left join gs_courses gs on gs.lti = c.id"""), con=connection)
        elif include_gs:
            courses = pd.read_sql(sql=text("""select cid as gs_course_id, gs.name as gs_name, null as canvas_name, shortname, year as term, lti as canvas_course_id, null as sis_course_id, null as start_at, null as end_at
                                    from gs_courses gs"""), con=connection)
        else:
            courses = pd.read_sql(sql=text("""select null as gs_course_id, null as gs_name, c.name as canvas_name, null as shortname, null as term, c.id as canvas_course_id, sis_course_id, start_at, end_at
                                    from canvas_courses gs"""), con=connection)
        
        courses['start_at'] = courses['start_at'].apply(lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ") if not pd.isna(x) else None)
        courses['end_at'] = courses['end_at'].apply(lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ") if not pd.isna(x) else None)
        
        return courses

def get_gs_assignments() -> pd.DataFrame:
    return pd.read_sql_table("gs_assignments", connection)

def get_canvas_assignments() -> pd.DataFrame:
    return pd.read_sql_table("canvas_assignments", connection)
    # return pd.read_csv('data/canvas_assignments.csv')

def get_aligned_assignments(include_gs: bool, include_canvas: bool) -> pd.DataFrame:
    with dbEngine.connect() as connection:
        if include_gs and include_canvas:
            assignments = pd.read_sql(sql=text("""select gs.id as gs_assignment_id, null as canvas_assignment_id, gs.course_id as gs_course_id, crs.lti as canvas_course_id, gs.name, strftime("%Y-%m-%dT%H:%M:%SZ", gs.assigned) as assigned, strftime("%Y-%m-%dT%H:%M:%SZ", gs.due) as due, null as canvas_max_points, "Gradescope" as source
                                                from gs_assignments gs join gs_courses crs on gs.course_id = crs.cid
                                                union
                                                select null as gs_assignment_id, c.id as canvas_assignment_id, null as gs_course_id, c.course_id as canvas_course_id, c.name as name, unlock_at as assigned, due_at as due, points_possible as canvas_max_points, "Canvas" as source
                                               from canvas_assignments c left join gs_courses crs on c.course_id = crs.lti
                                               """), con=connection)
        elif include_gs:
            assignments = pd.read_sql(sql=text("""select gs.id as gs_assignment_id, null as canvas_assignment_id, gs.course_id as gs_course_id, crs.lti as canvas_course_id, gs.name, strftime("%Y-%m-%dT%H:%M:%SZ", gs.assigned) as assigned, strftime("%Y-%m-%dT%H:%M:%SZ", gs.due) as due, null as canvas_max_points, "Gradescope" as source
                                    from gs_assignments gs join gs_courses crs on gs.course_id = crs.cid
                                    """), con=connection)
        else:
            assignments = pd.read_sql(sql=text("""select null as gs_assignment_id, c.id as canvas_assignment_id, null as gs_course_id, c.course_id as canvas_course_id, c.name as name, unlock_at as assigned, due_at as due, points_possible as canvas_max_points, "Canvas" as source
                                    from canvas_assignments c"""), con=connection)

        assignments['due'] = assignments['due'].apply(lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ") if not pd.isna(x) else None)
        assignments['assigned'] = assignments['assigned'].apply(lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ") if not pd.isna(x) else None)

        return assignments

def get_gs_submissions() -> pd.DataFrame:
    return pd.read_sql_table("gs_submissions", connection)

def get_canvas_submissions() -> pd.DataFrame:
    return pd.read_sql_table("canvas_submissions", connection)
    # return pd.read_csv('data/canvas_submissions.csv', low_memory=False)

def get_aligned_submissions(include_gs: bool, include_canvas: bool) -> pd.DataFrame:
    with dbEngine.connect() as connection:
        if include_gs and include_canvas:
            # student, email, [Total Score], [Max Points], Status, gs_submission_id, canvas_submission_id, [Submission Time], [Lateness (H:M:S)], student_id, 
            # gs_assignment_id, canvas_assignment_id, gs_student_id, gs_user_id, gs_course_id, canvas_course_id
            submissions = pd.read_sql(sql=text("""select [First Name] || " " || [Last Name] as student, Email as email, [Total Score], [Max Points], Status, 
                                               [Submission ID] as gs_submission_id, null as canvas_submission_id, [Submission Time], null as submitted_at, due,
                                               cast(st.student_id as int) as student_id, assign_id as gs_assignment_id, null as canvas_assignment_id, gsa.name,
                                               cast(st.sid as int) as gs_student_id, user_id as gs_user_id,gs.course_id as gs_course_id,gsc.lti as canvas_course_id, 
                                               case when gs.[Lateness (H:M:S)] > "00:00:00" then true else false end as late, 0 as points_deducted, gsc.shortname as course_name, "Gradescope" as source
                                               from gs_submissions gs left join gs_students st on gs.SID = cast(st.student_id as int) left join gs_courses gsc on gs.course_id=gsc.cid left join gs_assignments gsa on gs.assign_id = gsa.id
                                              union
                                               select st.name as student, st.email, score as [Total Score], a.points_possible as [Max Points], 
                                               case when graded_at is not null then "Graded" when submitted_at is not null then "Submitted" else "Missing" end as Status, 
                                               null as gs_submission_id, s.id as canvas_submission_id, null as [Submission Time], submitted_at, a.due_at as due,
                                               cast(sis_user_id as int) as student_id, null as gs_assignment_id, assignment_id as canvas_assignment_id, a.name, cast(gst.sid as int) as gs_student_id, 
                                               gst.user_id as gs_user_id, gsc.cid as gs_course_id,a.course_id as canvas_course_id, late, points_deducted, gsc.shortname as course_name, "Canvas" as source
                                               from canvas_submissions s join canvas_students st on s.user_id = st.id join canvas_assignments a on s.assignment_id = a.id 
                                               left join gs_students gst on cast(gst.student_id as int) = sis_user_id left join gs_courses gsc on gsc.lti = a.course_id
                                               """), con=connection)
        elif include_gs:
            # student, email, [Total Score], [Max Points], Status, gs_submission_id, canvas_submission_id, [Submission Time], [Lateness (H:M:S)], student_id, 
            # gs_assignment_id, canvas_assignment_id, gs_student_id, gs_user_id, gs_course_id, canvas_course_id
            submissions = pd.read_sql(sql=text("""select [First Name] || " " || [Last Name] as student, Email as email, [Total Score], [Max Points], Status, 
                                               [Submission ID] as gs_submission_id, null as canvas_submission_id, [Submission Time], null as submitted_at, due,
                                               cast(st.student_id as int) as student_id, assign_id as gs_assignment_id, null as canvas_assignment_id, gsa.name,
                                               cast(st.sid as int) as gs_student_id, user_id as gs_user_id,gs.course_id as gs_course_id,gsc.lti as canvas_course_id, 
                                               case when gs.[Lateness (H:M:S)] > "00:00:00" then true else false end as late, 0 as points_deducted, gsc.shortname as course_name, "Gradescope" as source
                                               from gs_submissions gs left join gs_students st on gs.SID = cast(st.student_id as int) left join gs_courses gsc on gs.course_id=gsc.cid left join gs_assignments gsa on gs.assign_id = gsa.id
                                    """), con=connection)
        else:
            # student, email, [Total Score], [Max Points], Status, gs_submission_id, canvas_submission_id, [Submission Time], [Lateness (H:M:S)], student_id,
            # gs_assignment_id, canvas_assignment_id, gs_student_id, gs_user_id, gs_course_id, canvas_course_id
            submissions = pd.read_sql(sql=text("""select st.name as student, st.email, score as [Total Score], a.points_possible as [Max Points], 
                                               case when graded_at is not null then "Graded" when submitted_at is not null then "Submitted" else "Missing" end as Status, 
                                               null as gs_submission_id, s.id as canvas_submission_id, null as [Submission Time], submitted_at, a.due_at as due,
                                               cast(sis_user_id as int) as student_id, null as gs_assignment_id, assignment_id as canvas_assignment_id, a.name, null as gs_student_id, null as gs_user_id, 
                                               null as gs_course_id, a.course_id as canvas_course_id, late, points_deducted, canvas_name as course_name, "Canvas" as source
                                               from canvas_submissions s join canvas_students st on s.user_id = st.id join canvas_assignments a on s.assignment_id = a.id"""), con=connection)

        submissions['Submission Time'] = submissions.apply(lambda x: datetime.strptime(x['submitted_at'], "%Y-%m-%dT%H:%M:%SZ") if not pd.isna(x['submitted_at']) else datetime.strptime(x['Submission Time'], '%Y-%m-%d %H:%M:%S %z') if not pd.isna(x['Submission Time']) else pd.NaT, axis=1)

        submissions['Submission Time'] = pd.to_datetime(submissions['Submission Time'], utc=True)
        submissions['due'] = pd.to_datetime(submissions['due'], utc=True)

        return submissions.drop(columns=['submitted_at'], axis=1)


def get_gs_extensions() -> pd.DataFrame:
    return pd.read_sql_table("gs_extensions", connection)

def get_canvas_extensions() -> pd.DataFrame:
    return pd.read_sql_table("canvas_extensions", connection)
    # return pd.read_csv('data/canvas_extensions.csv')