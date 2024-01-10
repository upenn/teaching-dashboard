#################################################################################
## components.py - Streamlit components for the Penn CIS Teaching Dashboard
##
## Renders different views of the student status data
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
from st_aggrid import AgGrid
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
from st_aggrid import GridOptionsBuilder, GridUpdateMode, DataReturnMode, AgGridTheme
import aggrid_helper
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

from status_tests import now
from entities import get_courses, get_assignments, get_course_enrollments, get_submissions
from views import get_scores_in_rubric, get_assignments_and_submissions

from status_tests import is_overdue, is_near_due, is_submitted, is_below_mean, is_far_below_mean, is_far_above_mean


def display_hw_status(course_name:str, assign:pd.DataFrame, due_date: datetime, df: pd.DataFrame) -> None:
    """
    Outputs, for each assignment, the student status
    """
    st.markdown('### %s'%assign['name'])
    # st.write('released on %s and due on %s'%(assigned,due))
    st.write('Due on %s'%(due_date.strftime('%A, %B %d, %Y')))

    # col1, col2 = st.tabs(['Students','Submissions by time'])

    by_time = df.copy().dropna()
    by_time['Submission Time'] = by_time['Submission Time'].apply(lambda x:pd.to_datetime(x, utc=True) if x else None)

    by_time = by_time.set_index(pd.DatetimeIndex(by_time['Submission Time']))

    by_time = by_time.groupby(pd.Grouper(freq='1D', label='right')).count()
    by_time = by_time[['Submission Time','Total Score']].rename(columns={'Submission Time': 'Day', 'Total Score':'Count'})
    # with col2:
    #     # st.write("Submissions over time:")
    #     st.line_chart(data=by_time,x='Day',y='Count')

    late_df = df[df.apply(lambda x: is_overdue(x, due_date), axis=1)]['email']
    late_as_list = str(late_df.to_list())[1:-2].replace('\'','').replace(' ','')
    
    last_minute_df = df[df.apply(lambda x: is_near_due(x, due_date), axis=1)]['email']
    last_minute_as_list = str(last_minute_df.to_list())[1:-2].replace('\'','').replace(' ','')

    # with col1:
        # st.write("Students and submissions:")
    st.dataframe(df.style.format(precision=0).apply(
        lambda x: [f"background-color:pink" 
                    if is_overdue(x, due_date) 
                    else f'background-color:mistyrose' 
                        if is_near_due(x, due_date) 
                        else 'background-color:lightgreen' if is_submitted(x) else '' for i in x],
        axis=1), use_container_width=True,hide_index=True,
                column_config={
                    'name':None,'sid':None,'cid':None,
                    'gs_assignment_id':None,'Last Name':None,'First Name':None, 
                    'assigned':None,'due': None,
                    'shortname':None,
                    # 'Sections':None,
                    'gs_course_id': None,
                    'gs_user_id': None,
                    'gs_student_id': None,
                    'canvas_sid': None,
                    'canvas_course_id': None,
                    'sis_course_id': None,
                    'Total Score':st.column_config.NumberColumn(step=1,format="$%d"),
                    'Max Points':st.column_config.NumberColumn(step=1,format="$%d"),
                    # 'Submission Time':st.column_config.DatetimeColumn(format="D MM YY, h:mm a")
                    })
        
    if len(late_df) > 0 and len(late_df) < 20:
        URL_STRING = "mailto:" + late_as_list + "?subject=Late homework&body=Hi, we have not received your submission for " + assign['name'] + " for " + course_name.strip() + ". Please let us know if you need special accommodation."

        st.markdown(
            f'<a href="{URL_STRING}" style="display: inline-block; padding: 12px 20px; background-color: #4CAF50; color: white; text-align: center; text-decoration: none; font-size: 16px; border-radius: 4px;">Email late students</a>',
            unsafe_allow_html=True
        )
    if len(last_minute_df) > 0 and len(last_minute_df) < 20:
        URL_STRING = "mailto:" + last_minute_as_list + "?subject=Approaching deadline&body=Hi, as a reminder, " + assign['name'] + " for " + course_name.strip() + " is nearly due. Please let us know if you need special accommodation."

        st.markdown(
            f'<a href="{URL_STRING}" style="display: inline-block; padding: 12px 20px; background-color: #4CAF50; color: white; text-align: center; text-decoration: none; font-size: 16px; border-radius: 4px;">Email reminder about deadline</a>',
            unsafe_allow_html=True
        )

def display_course(course_filter: pd.DataFrame):
    """
    Given a course dataframe (with a singleton row), displays for each assignment (in ascending order of deadline):
    - a line chart of submissions over time
    - a table of students, with color coding for overdue, near due, and submitted
    """

    courses_df = get_courses()
    course = courses_df[courses_df['shortname']==course_filter].iloc[0]

    st.write("Status of {}, {}:".format(course['shortname'], int(course['canvas_course_id'])))
    course_num = int(course['canvas_course_id'])
    course_name = course['name']

    col1, col2, col3, col4, col5 = st.tabs(['Status','Grading','Students','Submissions','Assignments'])

    with col1:
       grading_dfs = get_scores_in_rubric(display_rubric_component, course)

    with col2:
        courses = []
        for course_sheet in grading_dfs:
            if len(course_sheet):
                courses.append(course_sheet.iloc[0]['canvas_sid'])

        tabs = st.tabs([str(int(x)) for x in courses])

        for inx, course in enumerate(courses):
            this_course = grading_dfs[inx]

            with tabs[inx]:
                assign_grades(this_course)

    with col3:
        display_hw_totals(course_num)

    with col4:
        display_hw_assignment_scores(course_num)

    with col5:
        display_hws(course_name, course_num)

def display_birds_eye(birds_eye_df: pd.DataFrame) -> None:
    """
    Bird's eye view of student progress
    """
    overdue = 0
    pending = 0
    birds_eye_df.style.apply(
                lambda x: [f"background-color:pink" 
                            if overdue >0
                            else f'background-color:mistyrose' 
                                if pending >0
                                else 'background-color:lightgreen' for i in x],
                axis=1)
    
    gb = GridOptionsBuilder.from_dataframe(birds_eye_df)
                
    #### Add hyperlinks
    # gb.configure_column(
    #     "Course",
    #     headerName="Course",
    #     width=100,
    #     cellRenderer=aggrid_helper.add_url('Course', '/#status-of-cis-5450-2023-fall-big-data-analytics-on-campus')
    # )
    other_options = {'suppressColumnVirtualisation': True}
    gb.configure_grid_options(**other_options)

    gridOptions = gb.build()
    gridOptions['getRowStyle'] = aggrid_helper.add_highlight('params.data["😅"] > 0 || params.data["😰"] > 0', 'black', 'mistyrose')

    st.write("Overall status:")
    grid = AgGrid(
        birds_eye_df,
        gridOptions=gridOptions,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        allow_unsafe_jscode=True
        )
    
def display_rubric_component(title: str, column: str, max_column: str, dataframe: pd.DataFrame) -> None:
    """
    Helper function: given a dataframe representing a component of the rubric, displays a table with color coding
    and all students.
    """
    st.markdown('### %s'%title)
    if column and len(dataframe):
        mean = dataframe[column].dropna().mean()
        overall_max = dataframe[max_column].dropna().max()

        if not pd.isna(mean) and not pd.isna(overall_max):
            st.write('Mean: {:.2f}, Max: {}'.format(mean, overall_max))
        elif not pd.isna(mean):
            st.write('Mean: {:.2f}'.format(mean))
        elif not pd.isna(overall_max):
            st.write('Max: {}'.format(overall_max))
        st.dataframe(dataframe.style.format(precision=0).apply(
            lambda x: [f"background-color:pink" 
                        if is_far_below_mean(x, mean, column) 
                        else f'background-color:mistyrose' 
                            if is_below_mean(x, mean, column) 
                            else 'background-color:lightgreen' 
                                    if is_far_above_mean(x, overall_max, mean, column)
                                    else '' for i in x],
            axis=1), use_container_width=True,hide_index=True)
    else:
        st.dataframe(dataframe, use_container_width=True,hide_index=True)

def display_hw_assignment_scores(course = None) -> None:
    """
    For an optionally restricted course, shows the scores for each assignment
    """
    st.markdown('## Student Scores by Assignment')

    scores = get_assignments_and_submissions()
    if course is not None:
        scores = scores[scores['canvas_course_id'] == course]

    scores = scores\
                [['name', 'due', 'student', 'email', 'Total Score', 'Status', 'late']].\
                sort_values(by=['due', 'name', 'Total Score'])

        #melt(id_vars=['First Name', 'Last Name', 'Email', 'Sections', 'course_id', 'assign_id', 'Submission ID', 'Total Score', 'Max Points', 'Submission Time', 'Status', 'Lateness (H:M:S)']).\

    st.dataframe(scores)


def assign_grades(grade_totals: pd.DataFrame) -> None:
    """
    Grading control, presents sliders for each grade threshold and displays the resulting distribution.
    """
    thresholds = {'A+': 97, 'A': 93, 'A-': 90, 'B+': 87, 'B': 83, 'B-': 80, 'C+': 77, 'C': 73, 'C-': 70, 'D+': 67, 'D': 60}

    cols = st.columns(len(thresholds))

    prior = 100
    for inx,grade in enumerate(thresholds):
        # thresholds[grade] = st.slider("Threshold for {}".format(grade), 0, prior, thresholds[grade])
        with cols[inx]:
            thresholds[grade] = float(st.text_input("{} ≥".format(grade), value=thresholds[grade]))
        # prior = thresholds[grade]

    grade_totals['grade'] = ''
    if "Comments" in grade_totals.columns:
        grade_totals['grade'] = grade_totals.apply(lambda x: "I" if not pd.isna(x['Comments']) and "incomplete" in x['Comments'].lower() else '', axis=1)

    thresholds['F'] = 0
    
    ## This is taking advantage of Python's ordered dictionaries
    for grade in thresholds:
        # grade_totals[grade] = grade_totals['Total Score'].apply(lambda x: 1 if x >= thresholds[grade] else 0)
        # st.write("Assessing {} grades".format(grade))
        grade_totals['grade'] = grade_totals.apply\
            (lambda x: x['grade'] if not pd.isna(x['grade']) and len(x['grade']) > 0 \
             else grade if x['Total Points'] >= thresholds[grade] else '', axis=1)

    distrib = grade_totals.groupby('grade').count()['Total Points']#.reset_index()
    fig, ax = plt.subplots()
    plt.ylabel('Number of students')
    plt.xlabel("(Proposed) Letter Grade")
    plt.title("Grade distribution")

    for grade in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', "I"]:
        if grade not in distrib:
            distrib[grade] = 0
    distrib = distrib[['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', "I"]]
    bars = ax.bar(distrib.index, distrib)#['Total Points'])
    ax.bar_label(bars)
    fig.show()

    st.pyplot(fig)
    st.dataframe(grade_totals[['student','student_id','email','Total Points','Comments','grade']].sort_values(by=['Total Points','student']), use_container_width=True,hide_index=True)


def display_hw_totals(course: int = None) -> None:
    """
    Aggregate status by student
    """
    st.markdown('## Student Aggregate Status: Points Earned')

    scores = get_assignments_and_submissions()
    if course is not None:
        scores = scores[scores['canvas_course_id'] == course]
    scores = scores.\
                            groupby(by=['email','student']).sum()['Total Score'].reset_index().\
                            sort_values(by=['Total Score'])

        #melt(id_vars=['First Name', 'Last Name', 'Email', 'Sections', 'course_id', 'assign_id', 'Submission ID', 'Total Score', 'Max Points', 'Submission Time', 'Status', 'Lateness (H:M:S)']).\

    mean  = scores['Total Score'].mean()

    st.markdown('Out of {} students, the mean score is {} out of {}'.format(int(len(scores)), int(mean), int(scores['Total Score'].max())))

    st.dataframe(scores.style.format(precision=0).apply(
        lambda x: [f"background-color:pink" 
                    if is_far_below_mean(x, mean) 
                    else f'background-color:mistyrose' 
                        if is_below_mean(x, mean) 
                        else 'background-color:lightgreen' for i in x],
        axis=1), use_container_width=True,hide_index=True,
                column_config={
                    'name':None,'sid':None,'cid':None,
                    'assign_id':None,
                    'assigned':None,'due': None,
                    'shortname':None,
                    'Sections': None,
                    'gs_course_id': None,
                    'user_id': None,
                    'student_id': None,
                    'canvas_sid': None,
                    'canvas_id': None,
                    'sis_course_id': None,
                    'Total Score':st.column_config.NumberColumn(step=1,format="$%d")
                    # 'Submission Time':st.column_config.DatetimeColumn(format="D MM YY, h:mm a")
                    })


def display_hws(course_name: str, course: int = None):
    scores = get_assignments_and_submissions()
    if course is not None:
        scores = scores[scores['canvas_course_id'] == course]

        assigns = scores[['gs_assignment_id','name','due']].drop_duplicates()

        for a,assign in assigns.iterrows():
            df = scores[scores['gs_assignment_id']==assign['gs_assignment_id']]

            if len(df):
                due = list(df['due'].drop_duplicates())[0]
                due_date = due

                with st.container():
                    # Skip homework if it's not yet due!
                    if now < due_date:
                        continue

                display_hw_status(course_name, assign, due_date, df)
        st.divider()
