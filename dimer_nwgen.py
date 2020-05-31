#!/usr/bin/python

import sys
import os
from argparse import ArgumentParser


def write_title(filename, args):
    with open(filename + ".nwin", 'w') as f:
        f.write('title "{}"\n\n'.format(filename))
        if args.mem != 0:
            f.write("memory {0} mb\n\n".format(args.mem))


def write_geometry(filename, xyz, args):
    n = int(xyz[0][:-1])
    if(filename.endswith("monomer_a")):
        dummy = ["x" + xyz[i] if i > n / 2 else xyz[i] for i in range(n + 1)]
    elif(filename.endswith("monomer_b")):
        dummy = ["x" + xyz[i] if i <= n / 2 and i != 0 else xyz[i] for i in range(n + 1)]
    else:
        dummy = xyz.copy()

    atoms = set()
    for line in xyz[1:]:
        atoms.add(line.split(' ')[0])

    dummy.insert(1, '\n')
    with open(filename + ".xyz", 'w') as f:
        f.write("".join(dummy))
    with open(filename + ".nwin", 'a') as f:
        f.write("geometry nocenter")
        if args.noautoz:
            f.write(" noautoz")
        if args.noautosym:
            f.write(" noautosym")
        f.write("\n")
        f.write("".join(["    " + line for line in dummy[2:]]))
        f.write('end\n\n')

    return atoms


def write_basis(filename, atoms, basis):
    with open(filename + ".nwin", 'a') as f:
        f.write("basis spherical\n")
        f.write("    * library {0}\n".format(basis))
        for atom in atoms:
            f.write("    x{0} library {1} {2}\n".format(atom, atom.lower(), basis))
        f.write("end\n\n")


def write_task(filename):
    with open(filename + ".nwin", 'a') as f:
        f.write("scf\n")
        f.write("    thresh 1.0e-8\n")
        f.write("end\n\n")
        f.write("task scf")


def write_MC_file(filename, dimer_filename, args):
    dimer = True if filename.endswith("dimer") else False

    with open(filename + ".mcin", 'w') as f:
        f.write("JOBNAME {0}.MP2_F12_VBX.cv_TRUE\n".format(filename))
        f.write("JOBTYPE ENERGY\n")
        f.write("TASK MP2\n")
        f.write("TASK MP2_F12_VBX\n")
        f.write("MP2CV_LEVEL 2\n")
        f.write("MC_TRIAL {0}\n".format(args.s))
        f.write("ELECTRON_PAIRS {0}\n".format(args.ep))
        f.write("ELECTRONS {0}\n".format(args.e))
        f.write("SEED_FILE {0}.MP2_F12_VBX.cv_TRUE.SEED\n".format(dimer_filename))
        f.write("DEBUG {0}\n".format("0" if dimer else "2"))
        f.write("SAMPLER DIRECT\n")
        f.write("TAU_INTEGRATION STOCHASTIC\n")
        f.write("GEOM {0}.xyz\n".format(filename))
        f.write("BASIS ../basis/{0}.basis\n".format(args.basis))
        f.write("MC_BASIS ../basis/{0}.mc_basis\n".format(args.basis))
        f.write("MOVECS\n")

        if args.movecs_dir:
            f.write("\t../movecs/{0}.movecs\n".format(filename))
        else:
            f.write("\t{0}.movecs\n".format(filename))

        f.write("END")


# molecule_name: just the molecular system, e.g. "c60" for "c60_dimer.xyz"
# molecule_info: additional info added, e.g. number of electron pairs
# TODO: clean this damn script up
def write_job_script(filenames, molecule_name, molecule_info, args):
    with open("run-nw.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
        for filename in filenames:
            if args.log:
                f.write("mpirun -np {1} nwchem {0}.nwin 2>&1 | tee -a {0}.log\n".format(filename, args.n))
            else:
                f.write("mpirun -np {1} nwchem {0}.nwin\n".format(filename, args.n))

    with open("run-mc.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
        for filename in filenames:
            if args.log:
                f.write("mpirun -np {1} MC_MPn_Direct {0}.mcin 2>&1 | tee -a {0}.log\n".format(filename, args.n))
            else:
                f.write("mpirun -np {1} MC_MPn_Direct {0}.mcin\n".format(filename, args.n))

    with open("queue-nw.sh", 'w') as f:
        jobname = molecule_name + molecule_info

        f.write("#!/usr/bin/env bash\n\n")
        line = "qsub "

        if args.mail != "NONE":
            line += "-m abe -M {0} ".format(args.mail)

        line += "-pe orte {1} -V -b n -N {0} -cwd ./run-nw.sh".format(jobname, args.n)
        f.write(line)

    with open("queue-mc.sh", 'w') as f:
        jobname = molecule_name + molecule_info

        f.write("#!/usr/bin/env bash\n\n")
        line = "qsub "

        if args.mail != "NONE":
            line += "-m abe -M {0} ".format(args.mail)

        line += "-pe orte {1} -V -b n -N {0} -cwd ./run-mc.sh".format(jobname, args.n)
        f.write(line)

    with open("../run-all-nw.sh", 'a') as f:
        f.write("cd {0}\n".format(molecule_name))
        f.write("./run-nw.sh\n")
        f.write("cd ..\n")

    with open("../run-all-mc.sh", 'a') as f:
        f.write("cd {0}\n".format(molecule_name))
        f.write("./run-mc.sh\n")
        f.write("cd ..\n")

    with open("../queue-all-nw.sh", 'a') as f:
        f.write("cd {0}\n".format(molecule_name))
        f.write("./queue-nw.sh\n")
        f.write("cd ..\n")

    with open("../queue-all-mc.sh", 'a') as f:
        f.write("cd {0}\n".format(molecule_name))
        f.write("./queue-mc.sh\n")
        f.write("cd ..\n")

    os.chmod("run-nw.sh", 0o755)
    os.chmod("run-mc.sh", 0o755)
    os.chmod("queue-nw.sh", 0o755)
    os.chmod("queue-mc.sh", 0o755)


def main(args):
    xyz_files = args.xyz_files

    with open("run-all-nw.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
    with open("run-all-mc.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
    with open("queue-all-nw.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
    with open("queue-all-mc.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")

    os.chmod("run-all-nw.sh", 0o755)
    os.chmod("run-all-mc.sh", 0o755)
    os.chmod("queue-all-nw.sh", 0o755)
    os.chmod("queue-all-mc.sh", 0o755)

    for input_xyz in xyz_files:
        molecule_name = input_xyz[:-10]

        # TODO: i think these can be trimmed to 1 line
        if args.dir_info:
            molecule_info = "_{0}E_{1}EP".format(args.e, args.ep)
        else:
            molecule_info = ""

        if args.dir_name != "NONE":
            output_dir = args.dir_name + molecule_info
        else:
            output_dir = molecule_name + molecule_info

        with open(input_xyz, "r") as f:
            xyz = f.readlines()
            xyz = [str(line).lstrip() for line in xyz if line != "\n"]
        filenames = (molecule_name + "_dimer",
                     molecule_name + "_monomer_a",
                     molecule_name + "_monomer_b")
        dimer_filename = filenames[0]

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        os.chdir(output_dir)

        for filename in filenames:
            write_title(filename, args)
            atoms = write_geometry(filename, xyz, args)
            write_basis(filename, atoms, args.basis)
            write_task(filename)
            write_MC_file(filename, dimer_filename, args)

        write_job_script(filenames, molecule_name, molecule_info, args)

        os.chdir("..")


if __name__ == "__main__":
    parser = ArgumentParser(description = "Generate NWChem and MC-MPn-Direct input files for dimer calculations from dimer XYZ files.")

    parser.add_argument("xyz_files", metavar = "xyz_files", type = str, nargs = '+', help = "Dimer XYZ files.")

    parser.add_argument("-n", metavar = "[NO. OF THREADS]", type = int, default = 16, help = "Specify number of threads to use. Default: 16")
    parser.add_argument("-s", metavar = "[NO. OF STEPS]", type = int, default = 4096, help = "Specify number of steps to use. Default: 4096")
    parser.add_argument("-ep", metavar = "[NO. OF ELECTRON PAIRS]", type = int, default = 64, help = "Specify number of electron pairs. Default: 64")
    parser.add_argument("-e", metavar = "[NO. OF ELECTRONS]", type = int, default = 32, help = "Specify number of electrons to use. Default: 32")
    parser.add_argument("--basis", type = str, default = "aug-cc-pvdz", help = "Specifies basis set. Default: aug-cc-pVDZ")
    parser.add_argument("--mem", type = int, default = 0, help = "Explicitly specify NWChem allocated memory per thread in MB.")
    parser.add_argument("--mail", type = str, default = "NONE", metavar = "[EMAIL]", help = "Send email when queued jobs are complete.")
    parser.add_argument("--dir-name", type = str, default = "NONE", help = "Specify name of created directory.")

    parser.add_argument("--log", action = "store_true", help = "Log NWChem and MC-MPn-Direct stdout and stderr using tee.")
    parser.add_argument("--noautoz", action = "store_true", help = "Enables noautoz option in NWChem.")
    parser.add_argument("--noautosym", action = "store_true", help = "Enables noautosym option in NWChem.")
    parser.add_argument("--movecs-dir", action = "store_true", help = "Use separately stored movecs from '../movecs'.")
    parser.add_argument("--dir-info", action = "store_true", help = "Include info on electrons and electorn pairs in directory name.")

    args = parser.parse_args()

    main(args)
