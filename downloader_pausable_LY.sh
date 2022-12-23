#!/bin/bash
#bash input: $url, $start_int, $max_int, $is_numbering, $strg_file_dir p.s. max_int use 0 if no ;d
#strg file require terminating end!
#can only provide $strg_file_dir when resume
#sed "s/#>/>/g"->log

config_file="config.ly"
temp_file="temp.ly"
log_file="../log.txt"
pause_file="../pause.ly"
download_dir="download"

just_resume=1

#obj
while [[ $# -gt 0 ]]; do
	case $1 in
		-url|--url)
		  url_template="$2"
		  shift # past argument
		  shift # past value
		  ;;
		-min|--min_int)
		  min_int="$2"
		  shift
		  shift
		  ;;
		-max|--max_int)
		  max_int="$2"
		  shift
		  shift
		  ;;
		-num|--is_numbering)	#use name from counter / strg file
		  is_numbering="$2"
		  shift
		  shift
		  ;;
		-log|--is_logging)
		  is_logging="$2"
		  shift
		  shift
		  ;;
		-strg|--strg_file)
		  strg_file=$(realpath "$2")
		  shift
		  shift
		  ;;
		-cookie|--cookie_file)
		  cookie_file=$(realpath "$2")
		  shift
		  shift
		  ;;
		*)
		  echo "unknown: '$1'"
		  shift
		  exit
		  ;;
	esac
done

if grep -q ";d" <<< "$url_template" ; then
	: ${max_int:=$((2**63-1))}
	: ${min_int:=0}
else
	max_int=0
	min_int=0
fi
: ${is_numbering:=1}
: ${is_logging:=1}
#end obj

function urldecode(){
	sed 's@+@ @g;s@%@\\x@g'| xargs -0 printf "%b"
}

function valid_filename(){	#$filename
	lock_name=$(sed -n 3p "$temp_file")	#l:$lock_name
	#lock_name="$2"

	f=$(basename -- "$1") 	#purge filename
	extension=".${f##*.}"
	name="${f%.*}"
	count=1
	while [ -f "$f" ] && [ "$f" != "$lock_name" ]; do	#break if locked
		f="$name"."$count$extension"
		count=$((count+1))
	done

	sed -i "3 s/.*/$f/" "$temp_file" #make lock file l:$lock_name
	printf "$f"
}

function strip_space(){
	sed -Ee "s/^[ ]+//g" -Ee "s/[ ]+$//g"
}

function grep_content_disposition(){	#$response headers
	dispos=$(grep -i "content-disposition:" <<< "$1")
	utf_8_dispos=$(grep -iEo "filename[^=]?+\*[^=]?+=[^;]+" <<< "$dispos" | tail -n1 | awk -F\' '{print $NF}' | tr -d '\r','\n')
	normal_dispos=$(grep -iEo "filename[^=*]?+=[^;]+" <<< "$dispos" | tail -n1 | awk -F\" '{print $(NF-1)}' | tr -d '\r','\n')
	[ "$utf_8_dispos" != "" ] && choosen_dispos="$utf_8_dispos" || choosen_dispos="$normal_dispos"
	choosen_dispos=$(strip_space <<< "$choosen_dispos" | urldecode)
	printf "$choosen_dispos"
}

function update_temp(){ #$current_strg_counter, $current_counter, $lock_name
	#echo "update: $1-$2-$3"
	printf "$1\n$2\n$3\n" > "$temp_file"
	#echo "--file--";cat "$temp_file";echo "----"
}

function debug_print_temp(){
	printf "\n--file--\n"; cat "$temp_file" | sed "s/\n/ /g"; printf "\n----"
}

function dl_resource(){ #$line
						#$url_template,$max_int,$line,$start_i,$current_strg_counter,$is_numbering,$cookie_file
	this_just_resume=$just_resume
	for ((i=current_counter;i<=max_int;i++))
	do
		[ "$this_just_resume" -eq 1 ] && this_just_resume=0 || update_temp "$current_strg_counter" "$i" ""
		[ -e "$pause_file" ] && exit

		#sed -i -e "5 s/.*/$5/" -e "6 s/.*/$i/" "$temp_file"
		#[ -e "$pause_file" ] && exit

		#printf "\nnewterm:\n"; debug_print_temp	#testing

		url=$(echo "$url_template" | sed -e "s|;s|$1|g" -e "s|;d|$i|g")
		#echo "$url"#;continue

		filename=""
		if [ "$is_numbering" -eq 0 ]; then
			if [ "$cookie_file" != "" ]; then
				response_header=$(curl -sLI "$url" -H @"$cookie_file")
			else
				response_header=$(curl -sLI "$url")
			fi
			#filename=$(grep -i "content-disposition:" <<< "$response_header" | tail | tr -d '\r','\n' | awk -F\' '{print $NF}'| urldecode)
			filename=$(grep_content_disposition "$response_header")
			[ "$filename" == "" ] && filename=$(grep -i "location:" <<< "$response_header" | tail -n1 | tr -d '\r','\n' | cut -d':' -f2- | strip_space | urldecode)

			filename=$(valid_filename "$filename")
			#printf "\nvar: $current_strg_counter $i $filename\nzf"
			#sed -i "3 s/.*/$filename/" "$temp_file" #make lock file l:$lock_name
		fi
		if [ "$filename" == "" ]; then
			if [ "$1" == "" ]; then
				filename="$i"
			else
				purged_line=$(basename -- "$1" | urldecode)
				if [ "$max_int" == 0 ] && [ "$min_int" == 0 ]; then
					filename="$purged_line"
				else
					filename="$i-$purged_line"
				fi
			fi
		fi

		printf "\n$filename" #>>../log.txt

		if [ "$cookie_file" != "" ]; then
			#$(curl -sL "$url" -H @"$cookie_file" -C- -o "$filename")	#resume mode
			status_code=$(curl -sL "$url" -f -w "%{http_code}" -H @"$cookie_file" -o "$filename")	#-w "%{http_code}"
		else
			#$(wget "$url" -q -c -O "$filename") #resume mode
			#$(wget "$url" -q -O "$filename")
			status_code=$(curl -sL "$url" -f -w "%{http_code}" -o "$filename")
		fi

		if [ "$?" -ne 0 ]; then
			rm -f "$filename"
			printf "[E] $status_code" #>>../log.txt
		else
			printf "[S]" #>>../log.txt
		fi

		#echo "	$current_strg_counter" "$i" "$this_lock_name" #testing

		#sed -i -e "5 s/.*/$5/" -e "6 s/.*/$i/" "$temp_file"
	done
}

#main

#read
[ ! -f "$config_file" ] && printf "$url_template\n$min_int\n$max_int\n$is_numbering\n$is_logging\n" > "$config_file"

[ ! -f "$temp_file" ] && printf "1\n$min_int\n\n" > "$temp_file"

url_template=$(sed -n 1p "$config_file")
min_int=$(sed -n 2p "$config_file")
max_int=$(sed -n 3p "$config_file")
is_numbering=$(sed -n 4p "$config_file")
is_logging=$(sed -n 5p "$config_file")

current_strg_counter=$(sed -n 1p "$temp_file")
current_counter=$(sed -n 2p "$temp_file")
#lock_name=$(sed -n 3p "$temp_file")
#end read

$(mkdir -p "$download_dir")
cd "$download_dir"
temp_file="../$temp_file"
if [ "$strg_file" == "" ]; then
	[ "$is_logging" -eq 1 ] && dl_resource "" | tee -a "$log_file" || dl_resource ""
else
	strg_max_line=$(wc -l < "$strg_file")
	for ((;current_strg_counter<=strg_max_line;current_strg_counter++))
	do
		#sed -i "4 s/.*/$j/" "$temp_file"
		line=$(sed -n "$current_strg_counter"p "$strg_file")
		[ "$is_logging" -eq 1 ] && dl_resource "$line" | tee -a "$log_file" || dl_resource "$line"
		just_resume=0
		current_counter=$min_int
	done
fi
