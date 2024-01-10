#################################################################################
## entities.py - data entities for the Penn CIS Teaching Dashboard
##
## Provides interfaces to data about courses, students, assignments, submissions,
## and extensions.  Also provides a cache for the data, to avoid repeated retrieval.
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

import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime
from dateutil.tz import *
from status_tests import now, date_format
from database import include_canvas_data, include_gradescope_data
from database import get_canvas_students, get_gs_students, get_gs_courses, get_canvas_courses
from database import get_gs_assignments, get_canvas_assignments, get_gs_submissions, get_canvas_submissions
from database import get_gs_extensions, get_canvas_extensions, get_aligned_courses, get_aligned_students
from database import get_aligned_assignments, get_aligned_submissions

timezone = datetime.now().astimezone().tzinfo
# offset = timezone.utcoffset(datetime.now())
# tzoffset = f"{offset.days * 24 + offset.seconds // 3600:+03d}:{offset.seconds % 3600 // 60:02d}"

@st.cache_data
def get_courses() -> pd.DataFrame:
    if include_gradescope_data:
        return get_aligned_courses(include_gradescope_data, include_canvas_data).rename(columns={'gs_name': 'name'})
    else:
        return get_aligned_courses(include_gradescope_data, include_canvas_data).rename(columns={'canvas_name': 'name'})

@st.cache_data
def get_students() -> pd.DataFrame:
    return get_aligned_students(include_gradescope_data, include_canvas_data)

@st.cache_data
def get_assignments() -> pd.DataFrame:
    return get_aligned_assignments(include_gradescope_data, include_canvas_data)

@st.cache_data
def get_submissions(do_all = False) -> pd.DataFrame:
    return get_aligned_submissions(include_gradescope_data, include_canvas_data)

@st.cache_data
def get_extensions() -> pd.DataFrame:
    # TODO: how do we merge homework extensions??
    if include_gradescope_data:
        # duelate = 'Release (' + timezone + ')Due (' + timezone + ')'
        duelate = 'Release ({})Due ({})'.format(timezone, timezone)
        release = 'Release ({})'.format(timezone)
        due = 'Due ({})'.format(timezone)
        late = 'Late Due ({})'.format(timezone)
        extensions = get_gs_extensions().\
            drop(columns=['Edit','Section', 'First & Last Name Swap', 'Last, First Name Swap', 'Sections', duelate, release, 'Time Limit','Extension Type'])

        extensions['Due'] = extensions[due].apply(lambda x: datetime.strptime(x, '%b %d %Y %I:%M %p') if x != '(no change)' and x != 'No late due date' and x != '--' and not pd.isnull(x) else None)
        extensions['Late'] = extensions[late].apply(lambda x: datetime.strptime(x, '%b %d %Y %I:%M %p') if x != '(no change)' and x != 'No late due date' and x != '--' and not pd.isnull(x) else None)

        extensions.drop(columns=[due, late], inplace=True)
        extensions.rename(columns={'course_id': 'gs_course_id_', 'assign_id': 'gs_assign_id_', 'user_id': 'gs_user_id_'}, inplace=True)
        # st.dataframe(extensions)
        
        return extensions
    elif include_canvas_data:
        return get_canvas_extensions().rename(columns={'id':'extension_id', 'user_id':'SID', 'assignment_id':'assign_id', 'course_id':'course_id', 'extra_attempts':'Extra Attempts', 'extra_time':'Extra Time', 'extra_credit':'Extra Credit', 'late_due_at':'Late Due', 'extended_due_at':'Extended Due', 'created_at':'Created At', 'updated_at':'Updated At', 'workflow_state':'Workflow State', 'grader_id':'Grader ID', 'grader_notes':'Grader Notes', 'grader_visible_comment':'Grader Visible Comment', 'grader_anonymous_id':'Grader Anonymous ID', 'score':'Score', 'late':'Late', 'missing':'Missing', 'seconds_late':'Seconds Late', 'entered_score':'Entered Score', 'entered_grade':'Entered Grade', 'entered_at':'Entered At', 'excused':'Excused', 'posted_at':'Posted At', 'assignment_visible':'Assignment Visible', 'excuse':'Excuse', 'late_policy_status':'Late Policy Status', 'points_deducted':'Points Deducted', 'grading_period_id':'Grading Period ID', 'late_policy_deductible':'Late Policy Deductible', 'seconds_late_deduction':'Seconds Late Deduction', 'grading_period_title':'Grading Period Title', 'late_policy_status':'Late Policy Status', 'missing_submission_type':'Missing Submission Type', 'late_policy_deductible':'Late Policy Deductible', 'seconds_late_deduction':'Seconds Late Deduction', 'grading_period_title':'Grading Period Title', 'missing_submission_type':'Missing Submission Type', 'late_policy_status':'Late Policy Status', 'missing_submission_type':'Missing Submission Type', 'late_policy_status':'Late Policy Status', 'missing_submission_type':'Missing Submission Type', 'late_policy_status':'Late Policy Status', 'missing_submission_type':'Missing Submission Type', 'late_policy_status':'Late Policy Status', 'missing_submission_type':'Missing Submission Type', 'late_policy_status':'Late Policy Status', 'missing_submission_type':'Missing Submission Type', 'late_policy_status':'Late Policy Status', 'missing_submission_type':'Missing Submission Type', 'late_policy_status':'Late Policy Status', 'missing_submission_type':'Missing Submission Type'})

@st.cache_data
def get_assignments_and_submissions() -> pd.DataFrame:
    '''
    Joins assignments and submissions, paying attention to course ID as well as assignment ID

    Also drops some duplicates
    '''

    # st.write('Courses')
    # st.dataframe(get_courses())
    # st.write('Students')
    # st.dataframe(get_students())
    # st.write('Assignments')
    # st.dataframe(get_assignments())
    # st.write('Submissions')
    # st.dataframe(get_submissions())

    return get_submissions()


def get_course_names():
    """
    Retrieve the (short) name of every course
    """
    return get_courses().rename(columns={'shortname':'Course'}).set_index('gs_course_id')[['Course']].dropna()

@st.cache_data
def get_course_enrollments() -> pd.DataFrame:
    """
    Information about each course, students, and submissions along with extensions
    """
    enrollments = get_assignments_and_submissions()

    enrollments_no_gs = enrollments[enrollments['gs_assignment_id'].apply(lambda x: pd.isna(x))]
    enrollments_gs = enrollments[enrollments['gs_assignment_id'].apply(lambda x: not pd.isna(x))].dropna(subset=['gs_user_id'])

    # st.dataframe(enrollments_gs.head(100))
    # st.dataframe(enrollments_no_gs.head(100))

    # print(enrollments.dtypes)
    enrollments_gs = enrollments_gs.astype({'gs_user_id': int, 'gs_course_id': int, 'gs_assignment_id': int})
    # st.write('Enrollments')
    # st.dataframe(enrollments.head(5000))
    # print(get_extensions().dtypes)
    enrollments_with_exts = enrollments_gs.\
        merge(get_extensions(), left_on=['gs_user_id','gs_assignment_id','gs_course_id'], right_on=['gs_user_id_','gs_assign_id_','gs_course_id_'], how='left').\
        drop(columns=['gs_course_id_','gs_assign_id_','gs_user_id_'])

    # print(enrollments_with_exts.dtypes)


    enrollments_with_exts.apply(lambda x: x['due'] if pd.isna(x['Due']) else x['Due'], axis=1)
    enrollments_with_exts.drop(columns=['Due','Late'], inplace=True)

    enrollments_with_exts = pd.concat([enrollments_with_exts, enrollments_no_gs])

    enrollments_with_exts = enrollments_with_exts.sort_values(['due','name','Status','Total Score','student'],
                                        ascending=[True,True,True,True,True])
    
    return enrollments_with_exts


