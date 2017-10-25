import requests
import sys
import os
import shutil
import subprocess

MAX_RETRIES = 3

def ensure_folder_exists(folder_name):
	if not os.path.exists(folder_name):
		os.makedirs(folder_name)

def write_request_content_to_file(request, filename, bool_append=False):
	write_mode = 'a' if bool_append else 'w'  # Specify whether to overwrite or append based on flag
	with open(filename, write_mode + 'b') as temp_file:  # Open the file for write
		for block in request.iter_content(1024):  # And write in chunks of 1024 bytes
			temp_file.write(block)

def try_to_request(url, max_retries=MAX_RETRIES):
	for n in range(max_retries):
		try:
			request = requests.get(url)
			request.raise_for_status()
			return request
		except Exception as err:
			print("Error on attempt {}/{} for url '{}': {}".format(n+1, max_retries, url, err.message))

	raise Exception("Unable to request url '{}' after {} tries :(".format(url, max_retries))

def count_m3u8_lines(request_m3u8):
	num_lines = 0  # Init counter
	for line in request_m3u8.text.splitlines():
		if line.startswith("#"): continue  # Ignore commented lines
		num_lines += 1  # Increase counter

	return num_lines

def download_m3u8(url_m3u8, url_prepend, video_name='myVideo.mp4', dir_output='', dir_temp='temp/'):
	# Pre-process file&folder names
	dir_output = os.path.abspath(dir_output)
	dir_temp = os.path.abspath(dir_temp)
	ensure_folder_exists(dir_output)
	ensure_folder_exists(dir_temp)
	output_filename = os.path.join(dir_output, video_name)
	temp_filename = os.path.join(dir_temp, "temp.ts")

	# Format url_prepend
	url_prepend = url_prepend.replace("https://", "http://")  # HTTPS doesn't work, so just force HTTP ;)
	if not url_prepend.endswith('/'): url_prepend += '/'  # Make sure url_prepend ends in a '/'

	# Request the m3u8 file
	try:
		request_m3u8 = try_to_request(url_prepend + url_m3u8)
	except Exception as err:
		print("ERROR: couldn't request m3u8 file! {}".format(err))
		return

	num_lines = count_m3u8_lines(request_m3u8)
	arr_valid_files = []
	for line in request_m3u8.text.splitlines():
		if line.startswith("#"): continue  # Ignore commented lines

		# Download segment
		try:
			request_line = try_to_request(url_prepend + line)
		except Exception as err:
			print("ERROR: couldn't request ts segment '{}'! {}".format(line, err))
			continue  # Keep going with the other segments

		# Write segment to file
		arr_valid_files.append(os.path.abspath(os.path.join(dir_temp, line)))
		write_request_content_to_file(request_line, arr_valid_files[-1])  # Write to its own segment file
		write_request_content_to_file(request_line, temp_filename, bool_append=True)  # And also write to combined final file (.ts files can be concatenated)
		print("[{:3d}/{:3d}] Successfully downloaded segment '{}' ({} KB)".format(len(arr_valid_files), num_lines, line, int(request_line.headers['Content-Length'])/1000))
		if len(arr_valid_files)>4: break

	# And convert to video output format using ffmpeg
	print("Finally, going to convert temp file '{}' into output '{}'...".format(temp_filename, output_filename))
	subprocess.call(["ffmpeg", "-i", temp_filename, "-acodec", "copy", "-vcodec", "copy", "-y", output_filename])
	print("Done!!! =)")

	delete_temp = str(raw_input("Do you want to remove temp folder?")).lower()
	if delete_temp=="y" or delete_temp=="yes":
		shutil.rmtree(dir_temp)  # Remove temp folder if user requests it
		print("Temp folder deleted!")


if __name__ == "__main__":
	url_prepend = "https://vs05.yourgamecam.com/vod/twincreeks-field5-homeplate-2017-10-24-0/"
	url_m3u8 = "chunklist_w903946043_ps49119000_pd21000.m3u8"
	if len(sys.argv) == 2:
		url_prepend, url_m3u8 = sys.argv[1].rsplit('/', 1)
	elif len(sys.argv) > 2:
		url_prepend = sys.argv[1]
		url_m3u8 = sys.argv[2]

	download_m3u8(url_m3u8, url_prepend)
