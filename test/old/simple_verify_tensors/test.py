__author__ = "Anders Logg (logg@simula.no)"
__date__ = "2009-03-15 -- 2009-03-15"
__copyright__ = "Copyright (C) 2009 Anders Logg"
__license__  = "GNU GPL version 3 or any later version"

from cppcode import tabulate_tensor_code, integral_types
from ufl.common import tstr
import sys, os, commands, pickle, numpy, shutil

# Forms that don't work with tensor representation
only_quadrature = ["FunctionOperators",
                   "QuadratureElement",
                   "TensorWeightedPoisson",
                   "PoissonDG",
                   "Biharmonic",
                   "Normals",
                   "FacetIntegrals",
                   "HyperElasticity"]

# Log file
logfile = None

def tabulate_tensor(representation, integral, integral_type, header):
    "Generate code and tabulate tensor for integral."

    print "  Checking %s..." % integral

    # Generate and compile code
    options = {"n": 100, "N": 1000, "integral": integral, "header": header}
    code = tabulate_tensor_code[integral_type] % options
    open("tabulate_tensor.cpp", "w").write(code)
    c = "g++ `pkg-config --cflags ufc-1` -Wall -Werror -o tabulate_tensor tabulate_tensor.cpp"
    (ok, output) = run_command(c, representation, integral)
    if not ok:
        return "GCC compilation failed"

    # Run code and get results
    (ok, output) = run_command("./tabulate_tensor", representation, integral)
    if not ok: return "Unable to tabulate tensor (segmentation fault?)"
    values = [float(value) for value in output.split(" ") if len(value) > 0]

    return numpy.array(values)

def get_integrals(form):
    "Extract all integral classes for form."
    integrals = []
    for integral_type in integral_types:
        for integral in commands.getoutput("grep ufc::%s %s | grep class" % (integral_type, form + ".h")).split("\n"):
            integral = integral.split(":")[0].split(" ")[-1].strip()
            if not integral == "" and not integral.endswith("_tensor") and not integral.endswith("_quadrature"):
                integrals.append((integral, integral_type))
    return integrals

def to_dict(tuples):
    "Convert list of tuples to dictionary."
    d = {}
    for t in tuples:
        d[t[0]] = t[1]
    return d

def run_command(command, representation="", integral=""):
    "Run system command and collect any errors."
    global logfile
    (status, output) = commands.getstatusoutput(command)
    if not status is 0:
        if logfile is None:
            logfile = open("../error.log", "w")
        s = "%s: %s" % (representation, integral)
        logfile.write(s + "\n" + len(s) * "-" + "\n")
        logfile.write(output + "\n\n")
    return (status == 0, output)

def check_results(values, reference):
    "Check results and print summary."

    num_failed = 0
    num_missing_value = 0
    num_missing_reference = 0
    num_diffs = 0
    print ""
    for representation in values:
        vals = values[representation]
        s = "Results for %s representation" % representation
        print s + "\n" + "-"*len(s) + "\n"
        tol = 1e-12
        results = []

        integrals = []
        for (integral, value, form) in vals + reference:
            if not integral in integrals and not (representation is "tensor" and form in only_quadrature):
                integrals.append(integral)

        vals = to_dict(vals)
        refs = to_dict(reference)

        for integral in integrals:
            if integral in vals and isinstance(vals[integral], str):
                result = vals[integral]
                num_failed += 1
            elif integral in vals and integral in refs:
                e = max(abs(vals[integral] - refs[integral]))
                if e < tol:
                    result = "OK" % e
                else:
                    result = "*** (diff = %g)" % e
                    num_diffs += 1
            elif not integral in vals:
                result = "missing value"
                num_missing_value += 1
            elif not integral in reference and not ("_tensor" in integral or "_quadrature" in integral):
                result = "missing reference"
                num_missing_reference += 1
            else:
                continue

            results.append((integral, result))
        print tstr(results, 100)

    if num_failed == num_missing_value == num_missing_reference == num_diffs:
        print "\nAll tensors verified OK"
        return 0

    if num_failed > 0:
        print "*** Compilation failed for %d integrals. See 'error.log' for details." % num_failed
    if num_missing_value > 0:
        print "*** Values missing for %d integrals." % num_missing_value
    if num_missing_reference > 0:
        print "*** References missing for %d integrals." % num_missing_reference
    if num_diffs > 0:
        print "*** Results differ for %d integrals." % num_diffs

    print ""
    print """The following test should fail for tensor representation (due to round-off errors):
mass_0_cell_integral_0:                     *** (diff = 1e-09)
"""
    print "The following forms for tensor representation should have 'missing values' (not supported):"
    print "\n".join(only_quadrature)

    return 1
    
def main(args):
    "Call tabulate tensor for all integrals found in demo directory."

    # Change to temporary folder and copy form files
    if not os.path.isdir("tmp"):
        os.mkdir("tmp")
    os.chdir("tmp")
    run_command("cp ../../../demo/*.ufl .")

    # Iterate over all form files
    forms = commands.getoutput("ls *.ufl | cut -d'.' -f1").split("\n")

    values = {}
    for representation, option in [("quadrature", ""), ("tensor", ""), ("quadrature", " -O")]:
        vals = []
        for form in forms:
            # Skip forms not expected to work with tensor representation
            if representation == "tensor" and form in only_quadrature:
                continue

            # Compile form
            print "Compiling form %s..." % form
            (ok, output) = run_command("ffc -r %s %s.ufl" % (representation + option, form), representation, form)
            if not ok:
                vals.append((form, "FFC compilation failed", ""))
                continue

            # Tabulate tensors for all integrals
            for (integral, integral_type) in get_integrals(form):
                vals.append((integral, tabulate_tensor(representation, integral, integral_type, form + ".h"), form))
        values[representation + option] = vals

    # Remove temporary directory
    os.chdir("..")
    shutil.rmtree("tmp")

    # Load or update reference values
    if os.path.isfile("reference.pickle"):
        reference = pickle.load(open("reference.pickle", "r"))
    else:
        print "Unable to find reference values, storing current values."
        pickle.dump(values["quadrature"], open("reference.pickle", "w"))
        return 0

    # Check results
    return check_results(values, reference)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))