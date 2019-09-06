import logging
import os
import re
import shutil
from subprocess import check_call, check_output

# User Environment Variables ===================================================

# Path to the working directory. A new ESMF installation will be checked out in
# this directory. Ideally, this directory should be empty.
WORKING_DIR = os.path.expanduser("~/sandbox")
# Tag to compare against (i.e. the previous release)
TAG1 = "ESMF_7_1_0r"
# TAG1 = "ESMF_8_0_0_beta_snapshot_47"
# Tag for the new release that contains the API changes
TAG2 = "ESMF_8_0_0_beta_snapshot_48"
LOGPATH = "esmf_api_changes.log"
LOGLVL = logging.INFO


logging.basicConfig(
    level=LOGLVL,
    format='[%(name)s][%(levelname)s][%(asctime)s]:: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOGPATH, mode='w'),
        logging.StreamHandler()
    ])

# ==============================================================================


def log(msg):
    logging.log(logging.INFO, msg)


def myrun(cmd, **kwargs):
    call_or_output = kwargs.pop("call_or_output", "call")
    if type(cmd) == str:
        cmd = cmd.split(' ')
    msg = "running {}".format(cmd)
    if 'stdout' in kwargs:
        msg += ", stdout=" + str(kwargs["stdout"])
    if 'stderr' in kwargs:
        msg += ", stderr=" + str(kwargs["stderr"])
    log(msg)
    if call_or_output == "call":
        check_call(cmd, **kwargs)
    else:
        check_output(cmd, **kwargs)


def main():
    log(check_output(['gcc', '--version']))
    log(check_output(['gfortran', '--version']))
    os.chdir(WORKING_DIR)
    log('current working directory is: {}'.format(os.getcwd()))
    esmf_dir = os.path.join(WORKING_DIR, "esmf-for-api-changes")
    if not os.path.exists(esmf_dir):
        myrun(['git', 'clone',  'git://git.code.sf.net/p/esmf/esmf', 'esmf-for-api-changes'])

    log('harvesting interface changes...')
    harvestInterfaceChanges(esmf_dir, TAG1, TAG2)


def parse(outputfile, files):
    """
    This routine harvests the ESMF Fortran APIs from the html version of the
    reference manual and puts them in a file for text based searches (grep).

    :param outputfile: file name of harvested APIs
    :param files: sorted list of html files to parse
    """

    START = 'INTERFACE'
    END = 'DESCRIPTION'
    # END_NOARGS = ['ARGUMENTS', 'RETURN VALUE', 'PARAMETERS', 'DESCRIPTION']

    with open(outputfile, "w") as OUTFILE:
        writeline = ""
        # write all lines between START and END
        for f in files:
            flag = False
            with open(f) as infile:
                for line in infile:
                    # this is END for no arguments
                    # if any(enditer in line for enditer in END_NOARGS):
                    # this is END for with arguments
                    if END in line:
                        if flag:
                            OUTFILE.write("\n")
                        flag = False
                    # write the line
                    if flag:
                        OUTFILE.write(writeline+" "+line)
                    # get the section number
                    if re.search("\..*\..* ESMF.* - ",line) != None:
                        writeline = line.split(" ")[0]
                    # this is START
                    if START in line:
                        flag = True


def gather_source_files(esmfdir):
    REFDOCDIR = os.path.join(esmfdir, "doc/ESMF_refdoc")

    if not os.path.exists(REFDOCDIR):
        raise ValueError("Directory: " + REFDOCDIR + " was not found")

    # have to get the files i want to search (all node*.html)
    files = []
    output = myrun("ls " + REFDOCDIR)
    listdir = output.split()
    for htmlfile in listdir:
        if 'node' in htmlfile:
            addfile = (os.path.join(REFDOCDIR, htmlfile))
            files.append(addfile)
    files.remove(os.path.join(REFDOCDIR, "footnode.html"))
    files.remove(os.path.join(REFDOCDIR, "node1.html"))
    files.remove(os.path.join(REFDOCDIR, "node2.html"))
    files.remove(os.path.join(REFDOCDIR, "node3.html"))

    # sort list and move 10 to after 9
    files.sort()
    files.append(files.pop(0))

    return files


def build_esmf_docs(esmfdir, tag):
    os.chdir(esmfdir)
    os.putenv("ESMF_DIR", esmfdir)
    myrun("git checkout master")
    myrun("git pull")
    myrun("git checkout " + tag)
    myrun("make distclean", call_or_output="output")
    with open(os.path.join(WORKING_DIR, 'esmf-api-changes-make-info-{}.out'.format(tag)), 'w') as f:
        myrun("make info", stdout=f, stderr=f)
    with open(os.path.join(WORKING_DIR, 'esmf-api-changes-make-{}.out'.format(tag)), 'w') as f:
        myrun("make", stdout=f, stderr=f)
    with open(os.path.join(WORKING_DIR, 'esmf-api-changes-make-doc-{}.out'.format(tag)), 'w') as f:
        myrun("make doc", stdout=f, stderr=f)


def do(esmfdir, outputfile, tag):
    TAGDATADIR = tag + "_data"
    DRYDIR = os.path.join(WORKING_DIR, TAGDATADIR)

    # Build ESMF docs and move appropriate doc files for transfer to local
    if not os.path.exists(DRYDIR):
        build_esmf_docs(esmfdir, tag)
        os.makedirs(DRYDIR)
    files = gather_source_files(esmfdir)
    for f in files:
        shutil.copy2(f, DRYDIR)

    log("parsing docs for tag {}; output file is: {}".format(tag, outputfile))
    parse(outputfile, files)


def harvestInterfaceChanges(esmfdir, tag1, tag2):
    """
    Main entry point for generating interface changes.

    :param str esmfdir: Full path to the ESMF directory (ESMF_DIR)
    :param str tag1: Git tag for the previous release
    :param str tag2: Git tag for the current release
    """

    output1 = "APIs-"+tag1+".out"
    output2 = "APIs-"+tag2+".out"
    diffile = "diff-"+tag1+"-"+tag2+".out"
    do(esmfdir, output1, tag1)
    do(esmfdir, output2, tag2)

    cmd = ["diff", output1, output2]
    with open(diffile, 'w') as f:
        myrun(cmd, stdout=f)


if __name__ == "__main__":
    main()
