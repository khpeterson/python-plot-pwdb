#!/bin/bash

function USAGE {
    echo "usage: $0 [-h] [-d] [-1] pwdbdir"
	echo "     -h: print this help"
	echo "     -d: download first, then unpack"
	echo "     -1: unpack v1 (2019), otherwise v2 (2024, CoW)"
	echo "pwdbdir: final target dir for unpacked files"
    echo ""
    echo "This script downloads the pwdb datasets from zenodo.org, verifies"
	echo "the checksums, and unpacks the csv, geo and wfdb files into pwdbdir."
}

UNAME=`uname`
if [[ "$UNAME" =~ "NT" ]]; then
	SEVEN_ZIP="7z"
else
	SEVEN_ZIP="7zz"
fi
WGET="wget"
GIT="git"

# check for dependencies: 7z, wget, git, md5/md5sum
WHICH_SEVEN_ZIP=`which $SEVEN_ZIP`
if [ $? -ne 0 ]; then
	echo "7-Zip is need to extract files"
	if [[ "$UNAME" =~ "NT" ]]; then
		echo "You can find an installer at https://www.7-zip.org/"
    else
		echo "Try brew install 7zip"
	fi
	exit 1;
fi

WHICH_WGET=`which $WGET`
if [ $? -ne 0 ]; then
	echo "wget is needed to download files"
	echo "Try brew install wget"
	exit 1;
fi
	
WHICH_GIT=`which $GIT`
if [ $? -ne 0 ]; then
	echo "git is needed to download files"
	echo "You can find an installer at https://git-scm.com/downloads"
	exit 1;
fi

function MD5SUM { 
	local file=$1
	if [[ "$UNAME" =~ "Darwin" ]]; then
		md5 -q $file
	else
		md5sum $file | awk '{print $1}'
	fi
}
		  
CLEAN_DOWNLOAD=0
DOWNLOAD_V1=0

optspec="hd1"
while getopts "$optspec" optchar; do
    case "${optchar}" in
        h)
            USAGE;
            exit 0
            ;;
        d)
			CLEAN_DOWNLOAD=1
            ;;
        1)
			DOWNLOAD_V1=1
            ;;
        *)
			USAGE;
			exit 0;
            ;;
    esac
done

shift $((OPTIND-1))
if [ $# -ne 1 ]; then
	USAGE;
	exit 0;
fi
PWDB_DIR=$1

if [ $DOWNLOAD_V1 -eq 1 ]; then

	DOWNLOAD_ROOT="$PWD/downloads/v1"

	# dest dir,src URL,expected checksum
	PWDB_ITEMS=(
		".,https://zenodo.org/records/3275625/files/geo.zip,4b1fba2da497094e6ad71fcee14b0f7e"
		".,https://zenodo.org/records/3275625/files/pwdb_haemod_params.csv,43e1244665e6cee6b77501102404b70a"
		".,https://zenodo.org/records/3275625/files/pwdb_model_configs.csv,8c3b4f2f86386b72250766aedea9db52"
		".,https://zenodo.org/records/3275625/files/pwdb_model_variations.csv,3f1987efbc131b2cab8e576807385d5b"
		".,https://zenodo.org/records/3275625/files/pwdb_onset_times.csv,1103ddc3852d6f2164b981582fad8d23"
		".,https://zenodo.org/records/3275625/files/pwdb_pw_indices.csv,87946898d39d5a6d894901ad39f6b546"
		"PWs,https://zenodo.org/records/3275625/files/PWs_wfdb.zip,c4c3c3ba8163ee1f4f1495d7a4e70d73"
		".,https://github.com/peterhcharlton/pwdb,"
	)

else

	DOWNLOAD_ROOT="$PWD/downloads/v2"

	# dest dir,src URL,expected checksum
	PWDB_ITEMS=(
		"Complete,https://zenodo.org/records/11397985/files/exported_data.7z,aa7c4f3f4680839de3c6a8a477a2091b"
		"ACA_A1,https://zenodo.org/records/11567853/files/exported_data.7z,49a5af4b2abf033e8628d1c5fb1f6fef"
		"ACoA,https://zenodo.org/records/11449121/files/exported_data.7z,ad40e4775910febee102df48ec92dee4"
		"PCA_P1,https://zenodo.org/records/11573814/files/exported_data.zip,6780cf81eee3a8e9cb18ce5715c8abd2"
		"PCoAs,https://zenodo.org/records/11565240/files/exported_data.7z,2dfcdd9963df24ab412a623ad3e4d160",
		"PCoA_PCA_P1,https://zenodo.org/records/11571907/files/exported_data.7z,97f1de6402bd9aec409737d940c0ded3"
		"PCoA,https://zenodo.org/records/11473121/files/exported_data.7z,af30dbe43ef3cb8d8e48970386d0edea",
		".,https://zenodo.org/records/12519322/files/pwdb_v2.zip,27e733c03e9122669d559e4b22760489"
	)

fi

# download
if [[ $CLEAN_DOWNLOAD -eq 1 ]]; then
	echo "*** clean download"
	rm -rf $DOWNLOAD_ROOT
	for item in "${PWDB_ITEMS[@]}"; do
		# Extract name and URL from the item
		IFS=',' read -r DEST_DIR URL EXPECTED_CHECKSUM <<< "$item"
		DOWNLOAD_DIR="$DOWNLOAD_ROOT/$DEST_DIR"
		mkdir -p $DOWNLOAD_DIR
		if [[ "$URL" =~ "github" ]]; then
			( cd $DOWNLOAD_DIR; $GIT clone $URL )
		else
			( cd $DOWNLOAD_DIR; $WGET -nv --show-progress $URL )
		fi
	done
fi

# compare checksums
for item in "${PWDB_ITEMS[@]}"; do
	# Extract name and checksum from the item
	IFS=',' read -r DEST_DIR URL EXPECTED_CHECKSUM <<< "$item"
	DOWNLOAD_DIR="$DOWNLOAD_ROOT/$DEST_DIR"
	DOWNLOAD_FILE="$DOWNLOAD_DIR/$(basename $URL)"
	if [ ! -e "$DOWNLOAD_FILE" ]; then
		echo "file not found: $DOWNLOAD_FILE"
		exit 1;
	fi
	if [ -z "$EXPECTED_CHECKSUM" ]; then
		echo "*** skipping checksum for $DOWNLOAD_FILE"
    else
		echo "*** comparing checksums for $DOWNLOAD_FILE"
		CHECKSUM=$(MD5SUM $DOWNLOAD_FILE)
		if [ "$CHECKSUM" != "$EXPECTED_CHECKSUM" ]; then
			echo "checksum mismatch for $DOWNLOAD_FILE: got $CHECKSUM, expected $EXPECTED_CHECKSUM"
			exit 1;
		fi
	fi
done

# unpack files
for item in "${PWDB_ITEMS[@]}"; do
	# Extract name from the item
	IFS=',' read -r DEST_DIR URL EXPECTED_CHECKSUM <<< "$item"
	DOWNLOAD_DIR="$DOWNLOAD_ROOT/$DEST_DIR"
	DOWNLOAD_FILE="$DOWNLOAD_DIR/$(basename $URL)"
	if [ ! -e "$DOWNLOAD_FILE" ]; then
		echo "file not found: $DOWNLOAD_FILE"
		exit 1;
	fi
	echo "*** unpacking $DOWNLOAD_FILE"
	if [[ "$DOWNLOAD_FILE" =~ "exported_data" ]]; then
		# data is consolidated, unpack what we need
		FILES_TO_UNPACK='*.csv geo/* PWs/wfdb/*'
		for f in $FILES_TO_UNPACK; do 
			f_dir=`dirname $f`
			UNPACK_DIR="$PWDB_DIR/$DEST_DIR/$f_dir"
			mkdir -p $UNPACK_DIR
			(cd $UNPACK_DIR; $SEVEN_ZIP e $DOWNLOAD_FILE $f)
		done
	else
		# unpack everything
		UNPACK_DIR="$PWDB_DIR/$DEST_DIR"
		mkdir -p $UNPACK_DIR
		if [ "${DOWNLOAD_FILE##*.}" == "zip" ]; then
			(cd $UNPACK_DIR; $SEVEN_ZIP x $DOWNLOAD_FILE )
		elif [ -f "$DOWNLOAD_FILE" ]; then
			cp $DOWNLOAD_FILE $UNPACK_DIR
		elif [ -d "$DOWNLOAD_FILE" ]; then
			cp -r $DOWNLOAD_FILE $UNPACK_DIR
		fi
	fi
done
