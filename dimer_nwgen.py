#!/usr/bin/python

import sys
import os
from argparse import ArgumentParser


def write_title(filename):
    with open(filename + ".nwin", 'w') as f:
        f.write('title "{}"\n\n'.format(filename))


def write_geometry(filename, xyz):
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
        f.write("geometry nocenter noautoz\n")
        f.write("".join(["    " + line for line in dummy[2:]]))
        f.write('end\n\n')

    return atoms


def write_basis(filename, atoms):
    with open(filename + ".nwin", 'a') as f:
        f.write("basis spherical\n")
        f.write("    * library aug-cc-pvdz\n")
        for atom in atoms:
            f.write("    x{} library {} aug-cc-pvdz\n".format(atom, atom.lower()))
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
        f.write("MC_TRIAL 1048576\n")
        f.write("ELECTRON_PAIRS {0}\n".format(args.ep))
        f.write("ELECTRONS {0}\n".format(args.e))
        f.write("SEED_FILE {0}.MP2_F12_VBX.cv_TRUE.SEED\n".format(dimer_filename))
        f.write("DEBUG {0}\n".format("0" if dimer else "2"))
        f.write("SAMPLER DIRECT\n")
        f.write("TAU_INTEGRATION STOCHASTIC\n")
        f.write("GEOM {0}.xyz\n".format(filename))
        f.write("BASIS ../basis/aug-cc-pvdz.basis\n")
        f.write("MC_BASIS ../basis/aug-cc-pvdz.mc_basis\n")
        f.write("MOVECS\n")
        f.write("\t{0}.movecs\n".format(filename))
        f.write("END")


def write_job_script(filenames, output_dir, args):
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

    with open("../run-all-nw.sh", 'a') as f:
        f.write("cd {0}\n".format(output_dir))
        f.write("./run-nw.sh\n")
        f.write("cd ..\n")

    with open("../run-all-mc.sh", 'a') as f:
        f.write("cd {0}\n".format(output_dir))
        f.write("./run-mc.sh\n")
        f.write("cd ..\n")

    os.chmod("run-nw.sh", 0o755)
    os.chmod("run-mc.sh", 0o755)


def main(args):
    xyz_files = args.xyz_files

    with open("run-all-nw.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
    with open("run-all-mc.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
    os.chmod("run-all-nw.sh", 0o755)
    os.chmod("run-all-mc.sh", 0o755)

    for input_xyz in xyz_files:
        output_dir = input_xyz[:-10]
        with open(input_xyz, "r") as f:
            xyz = f.readlines()
            xyz = [str(line).lstrip() for line in xyz if line != "\n"]
        filenames = (output_dir + "_dimer",
                     output_dir + "_monomer_a",
                     output_dir + "_monomer_b")
        dimer_filename = filenames[0]

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        os.chdir(output_dir)

        for filename in filenames:
            write_title(filename)
            atoms = write_geometry(filename, xyz)
            write_basis(filename, atoms)
            write_task(filename)
            write_MC_file(filename, dimer_filename, args)

        write_job_script(filenames, output_dir, args)

        os.chdir("..")


if __name__ == "__main__":
    parser = ArgumentParser(description = "Generate NWChem and MC-MPn-Direct input files for dimer calculations from dimer XYZ files.")
    parser.add_argument("-n", metavar = "[NO. OF THREADS]", type = int, default = 8, help = "Specify number of threads to use. Default: 8")
    parser.add_argument("-ep", metavar = "[NO. OF ELECTRON PAIRS]", type = int, default = 64, help = "Specify number of electron pairs. Default: 64")
    parser.add_argument("-e", metavar = "[NO. OF ELECTRONS]", type = int, default = 32, help = "Specify number of electrons to use. Default: 32")
    parser.add_argument("--log", action = "store_true", help = "Log NWChem and MC-MPn-Direct stdout and stderr using tee.")
    parser.add_argument("xyz_files", metavar = "xyz_files", type = str, nargs = '+', help = "Dimer XYZ files.")
    args = parser.parse_args()

    main(args)
