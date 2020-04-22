#!/usr/bin/python

import sys
import os


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
        f.write("basis\n")
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


def write_MC_file(filename):
    dimer = True if filename.endswith("dimer") else False

    with open(filename + ".mcin", 'w') as f:
        f.write("JOBNAME {0}.MP2_F12_VBX.cv_TRUE\n".format(filename))
        f.write("JOBTYPE ENERGY\n")
        f.write("TASK MP2\n")
        f.write("TASK MP2_F12_VBX\n")
        f.write("MP2CV_LEVEL 2\n")
        f.write("MC_TRIAL 1048576\n")
        f.write("ELECTRON_PAIRS 128\n")
        f.write("ELECTRONS 64\n")
        f.write("SEED_FILE {0}.MP2_F12_VBX.cv_TRUE\n".format(filename))
        f.write("DEBUG {0}\n".format("0" if dimer else "2"))
        f.write("SPHERICAL 0\n")
        f.write("SAMPLER DIRECT\n")
        f.write("TAU_INTEGRATION STOCHASTIC\n")
        f.write("GEOM {0}.xyz\n".format(filename))
        f.write("BASIS ../basis/aug-cc-pvdz.basis\n")
        f.write("MC_BASIS ../basis/aug-cc-pvdz.mc_basis\n")
        f.write("MOVECS {0}.movecs\n".format(filename))


def write_job_script(filenames, output_dir):
    with open("run-nw.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
        for filename in filenames:
            f.write("mpirun -np 8 nwchem {0}.nwin &> {0}.log\n".format(filename))

    with open("run-mc.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
        for filename in filenames:
            f.write("mpirun -np 8 MC_MPn_Direct {0}.nwin &> {0}.log\n".format(filename))

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


def main():
    input_xyz_list = sys.argv[1:]

    with open("run-all-nw.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
    with open("run-all-mc.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
    os.chmod("run-all-nw.sh", 0o755)
    os.chmod("run-all-mc.sh", 0o755)

    for input_xyz in input_xyz_list:
        output_dir = input_xyz[:-10]
        with open(input_xyz, "r") as f:
            xyz = f.readlines()
            xyz = [str(line).lstrip() for line in xyz if line != "\n"]
        filenames = (output_dir + "_dimer",
                     output_dir + "_monomer_a",
                     output_dir + "_monomer_b")

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        os.chdir(output_dir)

        for filename in filenames:
            write_title(filename)
            atoms = write_geometry(filename, xyz)
            write_basis(filename, atoms)
            write_task(filename)
            write_MC_file(filename)

        write_job_script(filenames, output_dir)

        os.chdir("..")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: dimer_nwgen.py [dimer XYZ file]")
        print("dimer XYZ file must end in '_dimer.xyz'")
    else:
        main()
