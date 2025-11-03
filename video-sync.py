import configparser
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # makes rendering the graph work
import matplotlib.pyplot as plt
import cv2
from PIL import Image

# A script to sync a video with its data using an onscreen graph


# Quonkboard's displayed mappings to Labjack's config names
quonkboard_to_labjack = {
    "load_cell":        "b_load_1",
    "star_load_cell":   "s_load_1",
    "feed_line_pt":     "pres_2",
    "cc_pt":            "pres_1",
    "pre_injection_pt": "pres_3",
    "ops_pt":           "pres_4"
}

# Labjack's config names to human-readable names
labjack_to_human = {
    "b_load_1":         "LC1 Axial Load",
    "s_load_1":         "LC2 STAR Axial Load",
    "pres_1":           "PT1 CC Pressure",
    "pres_2":           "PT2 Feedline Pressure",
    "pres_3":           "PT3 Injector Pressure",
    "pres_4":           "PT4 OPS Pressure"
}


# The necessary inputs are a video of the hotfire, a frame number, and an exact timestamp of that frame
# The frame doesn't need to be the first frame of firing or ignition or anything

# Frame 240 of hf3_nice.MOV corresponds to frame 579 of hf3_data.mp4

best_guesses = [
    # The displayed data at frame 579 of hf3_data.mp4 is the following (best guess):
    # feed_line_pt is just starting to increase again, ops_pt is increading, cc_pt is mostly constant, pre_injection_pt is decreasing
    # This is close to 18 seconds after ignition countdown began (ignition itself began at 3126 seconds since boot)
    # {
    #     "t_plus":            3145.13667,
    #     "frame_number":      240,  # frame number of the desired output video; manually matched to the data using the data video
    #     "load_cell":         "86.83",
    #     "star_load_cell":    "16.75",
    #     "feed_line_pt":      "825.66",
    #     "cc_pt":             "101.05",
    #     "pre_injection_pt":  "615.14",
    #     "ops_pt":            "957.04"  # could be 857.04
    # }
    #
    # # Next update (mid-update 2 frames later (=0.06666666666 sec), done 3 frames later):
    {
        "t_plus":            2/30 + 3145.13667,  # closest is actually at 3145.64667, 15/30 after the first
        "frame_number":      240 + 2,
        "load_cell":         "86.38",  # could be 68.38
        "star_load_cell":    "16.75",
        "feed_line_pt":      "828.16",  # could be 826.16 or 829.16
        "cc_pt":             "102.12",  # could be 107.12
        "pre_injection_pt":  "647.80",  # could be 547.80
        "ops_pt":            "958.70",  # could be 953.70
    },
    #
    # # Next update (4 frames after mid-update (=0.13333333333 sec)):
    # {
    #     "t_plus":            (2 + 4)/30 + 3145.13667,  # closest is at 3146.15333, 30.5/30 after the first, 15/30 after the previous
    #     "load_cell":         "63.04",  # could be 53.04
    #     "star_load_cell":    "16.94",  # could be 18.94
    #     "feed_line_pt":      "827.03",  # could be 827.83
    #     "cc_pt":             "100.35",  # could be 100.36
    #     "pre_injection_pt":  "479.57",  # could be 478.57
    #     "ops_pt":            "959.20"
    # },
    #
    # # Next update? (14 frames later (=0.46666666666 sec))
    # {
    #     "t_plus":            (2 + 4 + 14)/30 + 3145.13667,  # closest is at 3146.660, 45.7/30 after first, 15/30 after previous
    #     "load_cell":         "39.10",
    #     "star_load_cell":    "17.23",
    #     "feed_line_pt":      "828.83",  # could be 829.83
    #     "cc_pt":             "101.24",
    #     "pre_injection_pt":  "405.38",
    #     "ops_pt":            "959.54"
    # }
]

# Load unprocessed data (need to match with the values that were displayed on Quonkboard)
df = pd.read_csv('proxima-hf-2c/data-raw/raw.csv', sep=',')


# Find the best possible frame value using Hamming distance
# There can't be insertions, deletions, or transpositions, but there could be substitutions
# Values must be truncated (or rounded?) to two decimal points' precision
def modified_hamming_distance(str1, str2):
    # This is from stackoverflow somewhere!
    # return the number of substitutions that have been made between strings str1 and str2
    # This is also modified to return the maximum error if the lengths of the strings are not the same
    # Since I'm sure I know how long numbers are
    if len(str1) != len(str2) or ("-" in str1 and "-" not in str2) or ("-" not in str1 and "-" in str2):
        return max(len(str1), len(str2))
    return sum(s1 != s2 for s1, s2 in zip(str1, str2))


search_range = 5
# Start at search_range (e.g. 2) seconds before the earliest best guess
# For each best guess, calculate a combined Hamming error for each best guess
# Continue until search_range seconds after the latest best guess
hamming_errors = pd.DataFrame(columns=list(quonkboard_to_labjack.keys()) + ["Index", "Sum"])
for data_index, data_row in df[((best_guesses[0]["t_plus"] - search_range) <= df["Time (s)"]) & ((df["Time (s)"] <= best_guesses[-1]["t_plus"] + search_range))].iterrows():
    hamming_errors.loc[len(hamming_errors)] = [-1.0 for i in range(len(quonkboard_to_labjack.keys()) + 2)]
    hamming_errors.at[len(hamming_errors)-1, "Index"] = int(data_index)
    for col in quonkboard_to_labjack.keys():
        # if data_index == 943541:  # debug printing
        #     print(col, f"{data_row[quonkboard_to_labjack[col]]}", f"{data_row[quonkboard_to_labjack[col]]:.2f}",
        #           best_guesses[0][col],
        #           modified_hamming_distance(f"{data_row[quonkboard_to_labjack[col]]:.2f}", best_guesses[0][col]))
        # if col == "cc_pt":  # debug plotting
        #     plt.plot(data_row["Time (s)"], data_row[quonkboard_to_labjack[col]], '.')
        hamming_errors.at[len(hamming_errors)-1, col] = modified_hamming_distance(f"{data_row[quonkboard_to_labjack[col]]:.2f}", best_guesses[0][col])  # hamming distance
        # hamming_errors.at[len(hamming_errors) - 1, col] = abs(data_row[quonkboard_to_labjack[col]] - float(best_guesses[0][col]))  # numeric difference
    hamming_errors.at[len(hamming_errors)-1, "Sum"] = sum([hamming_errors.at[len(hamming_errors)-1, col]**2 for col in quonkboard_to_labjack.keys()])

print("Min Hamming Error : ", min(hamming_errors["Sum"]))
frame_data = df.loc[hamming_errors[hamming_errors["Sum"] == min(hamming_errors["Sum"])].iloc[0]["Index"]]
frame_time = frame_data["Time (s)"]
best_guesses[0]["t_plus"] = frame_time
# Now we have a time value for the specific frame in the video

# Correct calibration
# Load config.ini
config = configparser.ConfigParser()
config.read("proxima-hf-2c\\config.ini")
# Calibration values are in the "conversion" section
recalibrations = [
    {
        "current_name": quonkboard_to_labjack["cc_pt"],
        "current_scale": float(config["conversion"][f"{quonkboard_to_labjack["cc_pt"]}_scale"]),
        "current_offset": float(config["conversion"][f"{quonkboard_to_labjack["cc_pt"]}_offset"]),
        "new_name": quonkboard_to_labjack["cc_pt"],
        "new_scale": float(config["conversion"][f"{quonkboard_to_labjack["pre_injection_pt"]}_scale"]),
        "new_offset": float(config["conversion"][f"{quonkboard_to_labjack["pre_injection_pt"]}_offset"])
    },
    {
        "current_name": quonkboard_to_labjack["pre_injection_pt"],
        "current_scale": float(config["conversion"][f"{quonkboard_to_labjack["pre_injection_pt"]}_scale"]),
        "current_offset": float(config["conversion"][f"{quonkboard_to_labjack["pre_injection_pt"]}_offset"]),
        "new_name": quonkboard_to_labjack["pre_injection_pt"],
        "new_scale": float(config["conversion"][f"{quonkboard_to_labjack["cc_pt"]}_scale"]),
        "new_offset": float(config["conversion"][f"{quonkboard_to_labjack["cc_pt"]}_offset"])
    },
]
decalib_df = pd.DataFrame()

subsection_df = df[((best_guesses[0]["t_plus"] - search_range) <= df["Time (s)"]) & ((df["Time (s)"] <= best_guesses[-1]["t_plus"] + search_range))]
plt.plot(subsection_df["Time (s)"], subsection_df[quonkboard_to_labjack["feed_line_pt"]], label="Feedline")
plt.plot(subsection_df["Time (s)"], subsection_df[quonkboard_to_labjack["ops_pt"]], label="OPS")
plt.plot(subsection_df["Time (s)"], subsection_df[quonkboard_to_labjack["cc_pt"]], label="CC Pre")
plt.plot(subsection_df["Time (s)"], subsection_df[quonkboard_to_labjack["pre_injection_pt"]], label="Inj Pre")

# Need to iterate twice to be able to correctly swap two columns

# Decalibrating - values back to the original sensor voltages
for recalib in recalibrations:
    decalib_df[recalib["current_name"]] = df[recalib["current_name"]] * recalib["current_scale"] + recalib["current_offset"]

# Recalibration - voltages back to new values
for recalib in recalibrations:
    df[recalib["new_name"]] = (decalib_df[recalib["current_name"]] - recalib["new_offset"]) / recalib["new_scale"]

subsection_df = df[((best_guesses[0]["t_plus"] - search_range) <= df["Time (s)"]) & ((df["Time (s)"] <= best_guesses[-1]["t_plus"] + search_range))]
# plt.plot(subsection_df["Time (s)"], subsection_df[quonkboard_to_labjack["cc_pt"]], label="CC Post")
# plt.plot(subsection_df["Time (s)"], subsection_df[quonkboard_to_labjack["pre_injection_pt"]], label="Inj Post")
# plt.legend()
# plt.show()

# Draw on top of video
video_path = "proxima-hf-2c\\hf3_nice.MOV"
output_path = "proxima-hf-2c\\graph_video.mp4"

video_start_time = best_guesses[0]["t_plus"] - best_guesses[0]["frame_number"] / 30

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error: could not open video")
    exit()

fps = int(cap.get(cv2.CAP_PROP_FPS))
duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')

out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

frame_count = 0
while cap.isOpened():
    print(f"Rendering frame {frame_count}")
    ret, frame_arr = cap.read()
    if not ret:
        break
    frame_img = Image.fromarray(frame_arr)

    # Generate graphic
    plt.cla()
    relevant_df = df[(video_start_time <= df["Time (s)"]) & (df["Time (s)"] <= (video_start_time + frame_count/30.0))]
    plt.plot(relevant_df["Time (s)"], relevant_df[quonkboard_to_labjack["feed_line_pt"]], label="Feedline")
    plt.plot(relevant_df["Time (s)"], relevant_df[quonkboard_to_labjack["cc_pt"]], label="CC")
    plt.plot(relevant_df["Time (s)"], relevant_df[quonkboard_to_labjack["pre_injection_pt"]], label="Pre-Inj")
    plt.plot(relevant_df["Time (s)"], relevant_df[quonkboard_to_labjack["ops_pt"]], label="OPS")
    plt.legend()
    plt.yticks(np.arange(0,1000,50))
    plt.xlim((video_start_time, video_start_time + duration))
    plt.title("Proxima HF2-C PT Data vs Time")
    plt.xlabel("Time (s)")
    plt.ylabel("Pressure (psig)")
    plt.grid()
    fig = plt.gcf()

    fig.canvas.draw()
    graph_img = Image.frombytes('RGBA', fig.canvas.get_width_height(), fig.canvas.tostring_argb())
    # ^ The RGBA channels are messed up, but we just need to be aware of that
    graph_arr = np.array(graph_img)
    graph_arr = np.stack((graph_arr[:, :, 1], graph_arr[:, :, 2], graph_arr[:, :, 3], graph_arr[:, :, 0]), axis=2)
    graph_img = Image.fromarray(graph_arr)
    # Resize image to be the correct size
    graph_img = graph_img.resize((frame_img.width, int(frame_img.width * graph_img.height / graph_img.width)))
    frame_img.paste(graph_img, (0,0))

    # Write frame
    out.write(np.array(frame_img))
    frame_count += 1

cap.release()
out.release()
cv2.destroyAllWindows()
print(f"Video saved to {output_path}")