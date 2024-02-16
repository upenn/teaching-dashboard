#################################################################################
## views.py - views for the Penn CIS Teaching Dashboard
##
## Basic multi-table views used to present grade status information
## within the Penn CIS Teaching Dashboard.
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
import pandas as pd
import yaml
import sys
from os import path

from entities import get_students, get_courses, get_assignments_and_submissions
from entities import get_course_enrollments

with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

def cap_points(row, rubric_items):
    '''
    If the student has earned more than the max points, cap it at the max points
    '''
    actual_score = row['Total Score']
    max_score = row['Max Points']

    if actual_score > max_score and 'max_extra_credit' in rubric_items \
        and actual_score > max_score + rubric_items['max_extra_credit']:
        # print(max_score)
        return max_score + rubric_items['max_extra_credit']
    else:
        # print(actual_score)
        return actual_score

def adjust_max(row, rubric_items):
    '''
    If the max points exceeds the maximum we specified in the rubric, cap it there
    '''
    max_score = row
    if 'max_score' in rubric_items and max_score > rubric_items['max_score']:
        max_score = rubric_items['max_score']

    return max_score

def sum_scaled(x, sums, maxes, scales):
    '''
    Scale the score components according to the rubric, and sum them up
    '''
    total = 0
    for i in range(len(sums)):
        if not pd.isnull(x[sums[i]]):
            if x[maxes[i]] == 0:
                total += x[sums[i]]
            else:
                total += x[sums[i]] * float(scales[i]) / float(x[maxes[i]])
    return total

def get_scores_in_rubric(output: callable, course:pd.Series = None) -> list[pd.DataFrame]:
    '''
    Returns a list of dataframes, one for each course, with overall grade scoring information.

    Along the way, it creates a series of dataframes for each rubric item.  It calls the output function
    to display the rubric item in the UI.
    '''
    courses = get_courses()
    if course is not None:
        courses = courses[courses['gs_course_id'] == course['gs_course_id']]

    grading_dfs = []
    for inx, course in courses.drop_duplicates().iterrows():
        # TODO: late??
        course_id = int(course['canvas_course_id'])

        st.write('For course {}, {}'.format(course_id, course['name']))
        sums = []
        scales = []
        scores = get_assignments_and_submissions()
        if course_id in config['rubric']:
            students = get_students()
            total = len(students)

            # Make sure we account for nulls
            students1 = students[students['gs_course_id'] == course['gs_course_id']].drop(columns=['gs_course_id', 'canvas_course_id'], axis=1)
            students2 = students[students['canvas_course_id'] == course['canvas_course_id']].drop(columns=['gs_course_id', 'canvas_course_id'], axis=1)
            
            students = pd.concat([students1, students2]).drop_duplicates()
            students.fillna(0, inplace=True)
            students = students.astype({'student_id': int})
            for group in config['rubric'][course_id]:
                if group == 'spreadsheet':
                    continue
                the_course = scores[scores['gs_course_id'] == course['gs_course_id']]

                # The subset we want -- just those matching the substring
                assigns = the_course[the_course['name'].apply(lambda x: str(config['rubric'][course_id][group]['substring']).lower() in x.lower())]

                # If we have filtered to one source (Gradescope or Canvas), make sure we eliminate any others
                if 'source' in config['rubric'][course_id][group]:
                    assigns = assigns[assigns['source'].apply(lambda x: x.upper() == str(config['rubric'][course_id][group]['source']).upper())]

                # Now we want to group by student and email, and sum up all assignments in this group
                if len(assigns):
                    assigns = assigns.groupby(by=['student', 'email', 'student_id']).\
                            sum().reset_index()\
                            [['student', 'Total Score', "Max Points", 'email', 'student_id']]
                
                if len(assigns):
                    assigns['Max Points'] = assigns['Max Points'].apply(lambda x: adjust_max(x, config['rubric'][course_id][group]))

                    # Cap the total points based on max + ec max
                    assigns['Total Score'] = assigns.apply(lambda x: cap_points(x, config['rubric'][course_id][group]), axis=1)

                    assigns = assigns.astype({'student_id': int})

                    students = students.merge(assigns[['student_id', 'Total Score', 'Max Points']].rename(columns={'Total Score': group, 
                                                                                                                   'Max Points': group + '_max', 
                                                                                                                   'student_id': 'student_id_'}), 
                                                                                                                   left_on='student_id', right_on='student_id_', 
                                                                                                                   how='left').drop(columns=['student_id_'])
                else:
                    students[group] = None
                    students[group + '_max'] = None

                if len(students) > total:
                    st.write("Error here, grew number of students")
                    st.dataframe(assigns)
                    total = len(students)

                sums.append(group)
                scales.append(config['rubric'][course_id][group]['points'])

                group_name = group[0].upper() + group[1:]
                if group_name[-1] >= '0' and group_name[-1] <= '9':
                    group_name = group_name[0:-1] + ' ' + group_name[-1]

                if 'source' in config['rubric'][course_id][group]:
                    if len(assigns):
                        assigns2 = assigns.drop(columns=['email'])
                    else:
                        assigns2 = assigns
                    output("{} ({})".format(group_name, config['rubric'][course_id][group]["source"]), 'Total Score', 'Max Points', assigns2)
                else:
                    output(group_name, 'Total Score', 'Max Points', assigns.drop(columns=['email']))

            # Look for optional file with additional fields
            ss = 'more-fields-{}.xlsx'.format(course_id)
            if "spreadsheet" in config['rubric'][course_id]:
                ss = config['rubric'][course_id]['spreadsheet']

            if path.isfile(ss):
                st.markdown ("## Additional Fields from Excel")
                more_fields = pd.read_excel('more-fields-{}.xlsx'.format(course_id)).drop(columns=['First Name', 'Last Name','Email'])
                
                students = students.merge(more_fields, left_on='student_id', right_on='SID', how='left').drop('SID', axis=1)
                for field in more_fields.columns:
                    if field != 'SID' and field != 'Comments':
                        sums.append(field)
                        if field != 'Adjustments':
                            students[field + '_max'] = max(students[field])
                            scales.append(max(students[field]))
                        else:
                            scales.append(0)
                            students[field + '_max'] = 0
                st.write('Adding {}'.format(more_fields.columns.to_list()))

            # scale and sum the points
            students['Total Points'] = students.apply(lambda x: sum_scaled(x, sums, [s + "_max" for s in sums], scales), axis=1)
            students['Max Points'] = students.apply(lambda x: sum_scaled(x, [s + "_max" for s in sums], [s + "_max" for s in sums], scales), axis=1)
            output('Total', 'Total Points', 'Max Points', students)

            grading = {}
            for col in students.columns:
                if not '_max' in col and not 'course_id' in col and col != 'gs_user_id':
                    grading[col] = students[col].values.tolist()

            grading_df = pd.DataFrame(grading)

            output('Grading', 'Total Points', 'Max Points', grading_df)

            grading_dfs.append(grading_df)

    return grading_dfs

def get_course_student_status_summary(
        is_overdue, 
        is_near_due, 
        is_submitted) -> pd.DataFrame:
    """
    Returns the number of total, submissions, overdue, and pending
    """

    course_col = 'gs_course_id'
    # name = 'shortname'
    due_date = 'due'
    # student_id = 'sid'

    enrollments = get_course_enrollments()
    # st.dataframe(enrollments.head(100))

    useful = enrollments.rename(columns={'gs_course_id': 'gs_course_id_', 'canvas_course_id': 'canvas_course_id_'}).merge(get_courses().drop(columns=['shortname','name']),left_on='gs_course_id_', right_on='gs_course_id').rename(columns={'shortname':'Course'})

    useful['😰'] = useful.apply(lambda x: is_overdue(x, x['due']), axis=1)
    useful['😅'] = useful.apply(lambda x: is_near_due(x, x['due']), axis=1)
    useful['✓'] = useful.apply(lambda x: is_submitted(x), axis=1)

    ids_to_short = enrollments[['gs_course_id','course_name']].drop_duplicates().rename(columns={'course_name':'Course'}).set_index('gs_course_id')

    return useful[[course_col,'😰','😅','✓']].groupby(course_col).sum().join(ids_to_short)[['Course','😰','😅','✓']]

