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


def write_job_script(filenames, output_dir):
    with open("run.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
        for filename in filenames:
            f.write("mpirun -np 6 nwchem {0}.nwin &> {0}.log\n".format(filename))

    with open("../run-all.sh", 'a') as f:
        f.write("cd {0}\n".format(output_dir))
        f.write("./run.sh\n")

    os.chmod("run.sh", 0o755)


def main():
    input_xyz_list = sys.argv[1:]
    with open("run-all.sh", 'w') as f:
        f.write("#!/usr/bin/env bash\n\n")
    os.chmod("run-all.sh", 0o755)

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

        write_job_script(filenames, output_dir)

        os.chdir("..")



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: dimer_nwgen.py [dimer XYZ file]")
        print("dimer XYZ file must end in '_dimer.xyz'")
    else:
        main()
