#input: $url, $min_int, $max_int, $strg_file_dir p.s. max_int use 0 if no ;d
import os, sys, argparse, re
import requests
import urllib.parse

config_file="config.ly"
temp_file="temp.ly"
log_file="../log.txt"
pause_file="../pause.ly"
download_dir="download"

just_resume=1

class Temp_data:
	def __init__(self, f_temp_arr):
		for i in range(0, 2):
			f_temp_arr[i] = int(f_temp_arr[i])
		self.current_strg_counter, \
		self.current_counter, \
		self.lock_name \
		 = f_temp_arr

	def __str__(self):
		return str(self.__dict__)


	def update_temp(self, f_temp):
		f_temp.seek(0)
		#f_temp.write('\n'.join(map(str, list(temp_data.values()))))
		f_temp.write('\n'.join(map(str, self.__dict__.values())))
		f_temp.write('\n')
		f_temp.truncate()
		#force flushing
		f_temp.flush()
		os.fsync(f_temp.fileno())

class Config_data:
	def __init__(self, f_config_arr):
		for i in range(1, 5):
			f_config_arr[i] = int(f_config_arr[i])
		self.url_template, \
		self.min_int, \
		self.max_int, \
		self.is_numbering, \
		self.is_logging, \
		 = f_config_arr

	def __str__(self):
		return str(self.__dict__)

#def convert_int(arr, start, end):
#	return_arr = arr
#	for i in range(start, end+1):
#		arr[i] = int(arr[i])
#	return return_arr

#def extract_cookie(cookie_file):
#	if cookie_file is not None:
#		cookies = {}
#		with open(cookie_file) as f_cookie:
#			#cookies = f_cookie.read().splitlines()
#			for cookies_lines in f_cookie:
#				cookies_split = cookies_lines.split(':', 1)
#				if cookies_split[0].lower().strip() == 'cookie':
#					for cookie in cookies_split[1].split(';'):
#						name, value = [i.strip() for i in cookie.split('=', 1)]
#						cookies.update({name: value})
#					return cookies
#	return None

def extract_headers(header_file):
	if header_file is not None:
		headers = {}
		with open(header_file) as f_header:
			for headers_lines in f_header:
				headers_split = headers_lines.split(':', 1)
				headers_split = [i.strip() for i in headers_split]
				headers.update({headers_split[0]: headers_split[1]})
		return headers
	return None
	
def valid_filename(f_temp, temp_data, filename):
	f = os.path.basename(filename)
	name, extension = os.path.splitext(f)		#diff with bash e.g. .bashrc
	count = 1
	while os.path.exists(f) and f != temp_data.lock_name:
		f = name+"."+str(count)+extension
		count += 1

	temp_data.lock_name = f
	temp_data.update_temp(f_temp)

	return f

def grep_content_disposition(dispos_strg):
	try:
		name = re.search("filename[^=]*\*[^=]*=[^;]*", dispos_strg, re.IGNORECASE)
		if name is not None:
			name = name.group()
			name = name[name.rindex("'")+1:]
		else:
			name = re.search('filename[^=*]*=[^;]*', dispos_strg, re.IGNORECASE)
			#print(name)
			if name is not None:
				name = name.group()
				name = name.split('"')
				#name = name[1:len(name)-2]
		return urllib.parse.unquote(name)
	except:
		print('grep_content_disposition exception, response headers')
		return None

def printf_log(f_log, strg, is_logging):	#f_log must be opened before call
	print(strg, end='')
	if is_logging:
		#force flushing
		f_log.write(strg)
		f_log.flush()
		os.fsync(f_log.fileno())

def dl_resource(f_temp, f_log, config_data, temp_data, line, headers):
	#equivalent:  "$cookie_file" != "" => headers != None
	#			  "$is_logging"	 != "" => f_log != None
	global just_resume
	for temp_data.current_counter in range(temp_data.current_counter, config_data.max_int+1):
		if just_resume:
			just_resume = 0
		else:
			temp_data.lock_name = ""
			temp_data.update_temp(f_temp)
		if os.path.exists(pause_file):
			exit

		url = config_data.url_template.replace(';s', line).replace(';d', str(temp_data.current_counter))
		#print(url)

		#if args.cookie_file is not None:
		#get header merged with downlod here
		if headers is not None:			#same as above
			r = requests.get(url, allow_redirects=True, headers=headers)
		else:
			r = requests.get(url, allow_redirects=True)

		#print(r.headers)

		filename = None
		if not config_data.is_numbering:
			if 'content-disposition' in r.headers:		#r.headers is caseinsensitive-type dict
				filename = grep_content_disposition(r.headers['content-disposition'])
			else:
				filename = urllib.parse.unquote(os.path.basename(r.url))
			filename = valid_filename(f_temp, temp_data, filename)

		if filename is None:
			if line == "":
				filename = str(temp_data.current_counter)
			else:
				purged_line = urllib.parse.unquote(os.path.basename(line))
				if config_data.max_int == '0':
					filename = purged_line
				else:
					filename = str(temp_data.current_counter)+'-'+purged_line

		printf_log(f_log, "\n"+filename, config_data.is_logging)

		try:
			byte = open(filename, 'wb').write(r.content)
			if byte > 0:
				printf_log(f_log, '[S]', config_data.is_logging)
			else:
				printf_log(f_log, '[E]', config_data.is_logging)
		except:
			printf_log(f_log, '[E] wf', config_data.is_logging)	#write file err

#		r = requests.get(url, allow_redirects=True, headers=headers)
#		if 'content-disposition' in r.headers:		#r.headers is caseinsensitive-type dict
#			fname = grep_content_disposition(r.headers['content-disposition'])
#			print(str(fname))
#		else:
#			fname = urllib.parse.unquote(os.path.basename(r.url))
#
#		print(fname, end='')
#		try:
#			byte = open(fname, 'wb').write(r.content)
#			if not byte > 0:
#				print('[E]')
#			else:
#				print('[S]')
#		except:
#			print('[E] wf')		#write file err
#
#		temp_data.update_temp(f_temp)


parser = argparse.ArgumentParser(description='Optional app description')
parser.add_argument('-url', '--url_template',
                    help='url template: [;d]:num_replace [;s]:strg_replace',
                    required=True)
parser.add_argument('-min', '--min_int',
                    help='counter start int')
parser.add_argument('-max', '--max_int',
                    help='counter end int')
parser.add_argument('-num', '--is_numbering',
                    help='use name from counter / strg file')
parser.add_argument('-log', '--is_logging',
                    help='write log')
parser.add_argument('-strg', '--strg_file',
                    help='string file')
parser.add_argument('-cookie', '--cookie_file',
                    help='cookie file')
args = parser.parse_args()

if args.strg_file is not None:
	args.strg_file = os.path.realpath(args.strg_file)
if args.cookie_file is not None:
	args.cookie_file = os.path.realpath(args.cookie_file)

if ";d" in args.url_template:
	args.max_int = str(2**63-1) if args.max_int is None else args.max_int
	args.min_int = '0' if args.min_int is None else args.min_int
else:
	args.max_int = '0'
	args.min_int = '0'
args.is_numbering = args.is_numbering or '1'
args.is_logging = args.is_logging or '1'

if not os.path.exists(config_file):
	with open(config_file, "w") as f_config:
		f_config.write('\n'.join([args.url_template,
								args.min_int,
								args.max_int,
								args.is_numbering,
								args.is_logging,
								'']))
if not os.path.exists(temp_file):
	with open(temp_file, "w") as f_temp:
			f_temp.write('\n'.join(['1',
									args.min_int,
									'',
									'']))

#read
with open(config_file, "r") as f_config:
	config_data = Config_data(f_config.read().splitlines())
	#print(str(config_data))	#testing

with open(temp_file, "r+") as f_temp:
	temp_data = Temp_data(f_temp.read().splitlines())
	#print(str(temp_data))		#testing
#end read

	if not os.path.exists(download_dir):
	   os.makedirs(download_dir)
	os.chdir(download_dir)
	temp_file = "../"+temp_file

	#log
	if config_data.is_logging is not None:
		f_log = open(log_file, "a")
	else:
		f_log = None
	#end log

	#cookie
	#cookies = extract_cookie(args.cookie_file)
	headers = extract_headers(args.cookie_file)
	#end cookie

	if args.strg_file is None:
		dl_resource(f_temp, f_log, config_data, temp_data, "", headers)
	else:
		with open(args.strg_file, "r") as f_strg:

			for j, line in enumerate(f_strg):
				if j+1 >= temp_data.current_strg_counter:
					#print("this_line: ", j, line, end='')
					line = line.rstrip('\r\n')
					temp_data.current_strg_counter = j+1
					dl_resource(f_temp, f_log, config_data, temp_data, line, headers)
					#just_resume = 0	#bash func cannot visit global var
					temp_data.current_counter = config_data.min_int

	#close log
	if config_data.is_logging is not None:
		f_log.close()
	#end close log
