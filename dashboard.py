#################################################################################
## dashboard.py - Penn CIS Teaching Dashboard
##
## Main StreamLit application for the Penn CIS Teaching Dashboard.
## Renders a view of student assignment completion, submission, and
## grading status.  Provides basic capabilities for assigning grades.
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
from entities import get_course_names

from components import display_course, display_birds_eye
from views import get_course_student_status_summary
from status_tests import is_overdue, is_near_due, is_submitted
from database import include_canvas_data, include_gradescope_data


name = ''
if include_gradescope_data:
    name = 'Gradescope'
if include_canvas_data:
    if len(name) > 0:
        name += '-'
    name += 'Canvas'

st.markdown("# Penn CIS {} Dashboard".format(name))
# Inject custom CSS to set the width of the sidebar
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 450px !important; # Set the width to your desired value
        }
    </style>
    """,
    unsafe_allow_html=True,
)


### Main dashboard is very simple.
### To the left, we have a "birds-eye" view of the course, showing the number of students
### and their progress on assignments.

### In the main view, there is a course selector with detailed data.

with st.sidebar:
    display_birds_eye(get_course_student_status_summary(
        is_overdue, is_near_due, is_submitted))

# Display the currently selected course contents
course_filter = st.selectbox("Select course", get_course_names())

display_course(course_filter=course_filter)