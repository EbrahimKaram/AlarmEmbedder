import json
import pandas as pd
import time

import re
from pyodide.http import open_url

import asyncio
from js import Uint8Array, File, URL, document
import io
from pyodide.ffi.wrappers import add_event_listener


url = "https://raw.githubusercontent.com/EbrahimKaram/AlarmEmbedder/main/"

legend_csv = f"{url}/Alarm_legend.csv"
function_number_csv = f"{url}/FunctionNumbersAxis.csv"
display_path = ""

is_RSS = True ## RSS or LSS
is_SSC = True ## FAB or SSC



legend_csv_df = pd.read_csv(open_url(legend_csv))
function_axis_csv_df = pd.read_csv(open_url(function_number_csv))


def plugAlarmsIn(row_index, o3, axis_name="stLid", function_number="-"):
    o3["alarms"] = [{"setpointA": int(row_index["setpointA"].values[0]),
                     "shelvingAllowed": bool(row_index["shelvingAllowed"].values[0]),
                     "ackMode": row_index["ackMode"].values[0],
                     # Name needs to include the function number in the Level 4 systems
                     "name": row_index["name"].values[0],
                     "displayPath": display_path,
                     "priority": row_index["priority"].values[0]}]

    o3["alarms"][0]["name"] = buildAlarmID(
        function_number=function_number, template_alarm_msg=row_index["name"].values[0], is_SSC=is_SSC)

    # Label could have just the message or it has a binding a expression which needs to change
    if (row_index['label'].isnull().values.any()):
        o3["alarms"][0]["label"] = {"bindType": row_index["bindType"].values[0].strip(),
                                    "value": row_index["value"].values[0].strip().replace("stLid", axis_name)}
        if (is_RSS):
            o3["alarms"][0]["label"]["value"] = o3["alarms"][0]["label"]["value"].replace(
                "LSS", "RSS")
        if (is_SSC):
            o3["alarms"][0]["label"]["value"] = o3["alarms"][0]["label"]["value"].replace(
                "FAB", "SSC")

    else:
        # Make sure to replace
        o3["alarms"][0]["label"] = row_index["label"].values[0].strip()
        if (is_RSS):
            o3["alarms"][0]["label"] = o3["alarms"][0]["label"].replace(
                "LSS", "RSS")
        if (is_SSC):
            o3["alarms"][0]["label"] = o3["alarms"][0]["label"].replace(
                "FAB", "SSC")
        
        
# We need to note that the function number needs to be 5 digits long for the SSC
# The name of the Alarm is formed as follows. FAB_2100 that can be dissected as follows FAB_(ElementNumber)(axisNumber)(messageNumber).
# In the FunctionNumbers CSV, we have the Function number for each axis, this made of element number and axis number
# Since Axis number can be more than two digits in an SSC

def buildAlarmID(function_number="001", template_alarm_msg="FAB_001", is_SSC=True):
    if (function_number == "-"):
        if (is_SSC):
            template_alarm_msg = template_alarm_msg.replace("FAB", "SSC")
        return template_alarm_msg

    alarm_message = ""
    # This gets the number after the _ in the template alarm message
    number_alarm_msg = re.findall(
        "(?<=\_)[0-9]*",template_alarm_msg)[0]
    # Alarm is the last two digits
    alarm_id = number_alarm_msg[-2:]

    alarm_prefix = "SSC_" if is_SSC else "FAB_"

    alarm_message = alarm_prefix+function_number+alarm_id

    return alarm_message

def getFunctionNumber(displayPath="FAB2900", element_name="GvVanityCase", axis_name="stLid"):

    mask = (function_axis_csv_df["FabNumber"] == display_path) & (
        function_axis_csv_df["Element"] == element_name) & (function_axis_csv_df["Axis"] == axis_name)

    # Sometimes Element name is not in the list so we need to check for that
    if ((element_name in function_axis_csv_df["Element"].values) and
        not (axis_name in function_axis_csv_df["Axis"].values) and
            axis_name.startswith("st")):
        print()
        print("Axis", axis_name, "was not found for element", element_name)
        print("Please Update FunctionNumbersAxis.csv")
        print()

    # There will be a case where there is no axis name, in that case we need to just get the first digit of the number

    if (len(function_axis_csv_df.loc[mask]) < 1):

        # Try to search with element name only
        mask = (function_axis_csv_df["FabNumber"] == display_path) & (
            function_axis_csv_df["Element"] == element_name)

        if (len(function_axis_csv_df.loc[mask]) < 1):
            print("No function number was found")
            return "-"
        else:
            # We want to make sure we return the first character of the string in this case
            return str(function_axis_csv_df.loc[mask].FunctionNumber.values[0]).zfill(2)[0]

    return str(function_axis_csv_df.loc[mask].FunctionNumber.values[0]).zfill(2)


def process_file(event):
    print("Hello World")


# Reference: https://pyscript.recipes/2024.1.1/basic/file-download/

data_string = "Hello world, this is some text."


def downloadFile(display_path=display_path,):
    print("Download was clicked")

    encoded_data = data_string.encode('utf-8')
    my_stream = io.BytesIO(encoded_data)

    js_array = Uint8Array.new(len(encoded_data))
    js_array.assign(my_stream.getbuffer())

    file = File.new([js_array], "unused_file_name.txt", {type: "text/plain"})
    url = URL.createObjectURL(file)

    hidden_link = document.createElement("a")
    hidden_link.setAttribute(
        "download", "Export_data_"+display_path+"_"+str(time.time())+"_.json")
    hidden_link.setAttribute("href", url)
    hidden_link.click()

# Reference: https://pyscript.recipes/2024.1.1/basic/file-upload/


async def uploadFileAndEmbedAlarms(*args):
    print("Upload was clicked")
    # We need to get the FabName is
    global display_path
    display_path = str(document.getElementById("fab_name").value).strip()
    print("Display path", display_path)

    global is_RSS
    is_RSS = document.querySelector("#is_RSS").checked
    print("Is this an RSS", is_RSS)

    global is_SSC
    is_SSC = document.querySelector("#is_SSC").checked
    print("Is this an SSC", is_SSC)

    # file=document.getElementById("file-upload").files.item(0)
    if (document.getElementById("file-upload").files.length > 0):
        await upload_file_and_show(document.getElementById("file-upload"))
    else:
        print("Please upload a file")
    # print(file.name)


async def upload_file_and_show(document_uploaded):
    file_list = document_uploaded.files
    file = document.getElementById("file-upload").files.item(0)
    print(file.name)
    json_data_string = await file.text()
    # print(json_data_string)
    process_info(json_data_string, display_path)

    # my_bytes: bytes = await get_bytes_from_file(first_item)
    # print(my_bytes[:200])  # Do something with file contents


add_event_listener(document.getElementById("download"), "click", downloadFile)
add_event_listener(document.getElementById("upload"),
                   "click", uploadFileAndEmbedAlarms)


def process_info(json_data_string, display_path):
    data = json.loads(json_data_string)
    for o1 in data["tags"]:
        print("Level 1", o1["name"])
        if ('tags' in o1.keys()):
            for o2 in o1["tags"]:
                # Example: Level 2 GvSewingPantsSewingShirt stAlarmBits
                print("Level 2", o1["name"], o2["name"])

                for o3 in o2["tags"]:
                    # Example: Level 3 GvSys stAlarmBits bTempLow
                    print("Level 3", o1["name"], o2["name"], o3["name"])
                    if (o3["name"] in legend_csv_df.tagName.values):
                        row_index = legend_csv_df.loc[legend_csv_df.tagName == o3["name"]]

                        # This is to check for the GvSys system. We want to try to filter the row index here.
                        # this is all for the two entries of bAlarmResetExceeded one for GvSys and one for the Figure itself
                        if (len(row_index) > 1):
                            mask = (legend_csv_df.tagName == o3["name"]) & (
                                legend_csv_df["parentTag"] == o1["name"])
                            row_index = legend_csv_df.loc[mask]

                            if (len(row_index) < 1):
                                mask = (legend_csv_df.tagName == o3["name"]) & (
                                    legend_csv_df["parentTag"] != "GvSys")
                                row_index = legend_csv_df.loc[mask]

                        function_number = getFunctionNumber(
                            displayPath=display_path, element_name=o1["name"], axis_name=o3["name"])
                        plugAlarmsIn(
                            row_index, o3, function_number=function_number)

                    if ('tags' in o3.keys()):
                        for o4 in o3["tags"]:
                            print("Level 4", o1["name"],
                                  o2["name"], o3["name"], o4["name"])
                            if (o4["name"] in legend_csv_df.tagName.values):
                                row_index = legend_csv_df.loc[legend_csv_df.tagName == o4["name"]]
                                function_number = getFunctionNumber(
                                    displayPath=display_path, element_name=o1["name"], axis_name=o3["name"])
                                plugAlarmsIn(
                                    row_index, o4, axis_name=o3["name"], function_number=function_number)
    global data_string
    data_string = json.dumps(data, indent=1)
    downloadFile(display_path)
