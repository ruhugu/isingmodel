import numpy as np
import random 
from matplotlib import pyplot as plt
from matplotlib import animation


class Results(object):
    def __init__(self, shape=None, fname=None):

        # If the filename is provided, read the data from there
        if fname != None:
            self.readtxt(fname)
        else:
            # Store parameters
            self.shape = list(shape)
            if self.shape == None:
                raise ValueError("Lattice shape not given.")

            # Initialize results lists
            self.Ts = list()
            self.mags = list()
            self.mag2s = list()
            self.mag4s = list()
            self.corrs = list()
            self.acceptprobs = list()
            self.nmeasures = list()
            self.measureintervals = list()

        # Calculate the numer of spins
        self.nspins = np.prod(self.shape)

    # TODO: complete docs
    # TODO: check if T has been already measured and average
    # with the previous data in that case
    def measure(self, T, nmeasures, latt, measureinterval=1):
        """Measure blablbalba

        """
        # Check if lattice shape is the expected one
        if self.shape != latt.shape():
            raise ValueError(
                    "The lattice shape does not match the Results object one.")
            
        # Store parameters
        self.Ts.append(T)
        self.nmeasures.append(nmeasures)
        self.measureintervals.append(measureinterval)

        # Initialize variables
        mag_last = 0. # Magnetization in the last measure
        mag_sum = 0.
        mag2_sum = 0.
        mag4_sum = 0.
        corr_sum = 0.
        naccept = 0

        # Start measure loop
        for measure_idx in range(nmeasures):
            # Evolve
            naccept += latt.evolve(measureinterval, T) 

            # Measure
            mag = latt.magnetization()
            mag_sum += np.abs(mag)
            mag2 = mag*mag
            mag2_sum += mag2
            mag4_sum += mag2*mag2
            corr_sum += mag*mag_last

            # Store last measure
            mag_last = mag

        # Store measures and calculate means
        self.mags.append(mag_sum/nmeasures)
        self.mag2s.append(mag2_sum/nmeasures)
        self.mag4s.append(mag2_sum/nmeasures)
        self.corrs.append(corr_sum/(nmeasures - 1))
        self.acceptprobs.append(
                float(naccept)/(nmeasures*measureinterval*latt.nspins))

        return


    # I/O 
    # ==============================
    def readtxt(self, filename):
        """Read data from file.

        """
        filedata = np.loadtxt(filename).T

        self.Ts = filedata[0].tolist()
        self.mags = filedata[1].tolist()
        self.mag2s = filedata[2].tolist()
        self.mag4s = filedata[3].tolist()
        self.corrs = filedata[4].tolist()
        self.acceptprobs = filedata[5].tolist()
        self.nmeasures = filedata[6].tolist()
        self.measureintervals = filedata[7].tolist()

        # Read additional parameters from footer
        with open(filename, "r") as f:
            lines = f.readlines()
            self.shape = map(int, lines[-1].split()[2].split(","))

        return

    def savetxt(self, fname=None):
        """Save data to file.

        Parameters
        ----------
            fname : string
                Name of the output file. Its default value is
                "isingR{0}C{1}.dat" with {0} the number of rows 
                in the lattice and {1} the number of columns.

        """
        if fname == None:
            fname = "isingR{0}C{1}.dat".format(self.shape[0], self.shape[1])

        headerstring = ("Temperature\t Mean mag.\t Mag. 2nd moment\t "
                "Mag. 4nd moment\t Mag. time corr.\t Acceptance probability\t "
                "N measures\t Measure interval")
        footerstring = "Shape: {0},{1}".format(self.shape[0], self.shape[1])

        np.savetxt(
                fname,
                np.vstack((
                        self.Ts, self.mags, self.mag2s, self.mag4s,
                        self.corrs, self.acceptprobs, self.nmeasures, 
                        self.measureintervals)).T,
                header=headerstring, footer=footerstring)
        return

        
    # Physical magnitudes
    # ========================================
    def mag_err(self):
        """Calculate the magnetization mean error.

        """
        return self.samplemean_error(
                self.mags, self.mag2s, self.acceptprobs, self.nmeasures)

    def binderratio(self):
        """Calculate the Binder ratio or fourth order cumulant.

        """
        return (1. - self.mag4s/(3.*np.power(self.mag2s, 2)))

    
    # Statistical functions
    # ===================================
    @staticmethod
    def variance(mean, momnt2):
        """Calculate the sample variance.

        Parameters
        ----------
            mean : float (scalar or array)
                Mean value. 

            momnt2 : float (scalar or array)
                Second raw moment (mean of the square).

        Returns
        -------
            variance : float (scalar or array)

        """
        momnt2_arr = np.array(momnt2)
        return momnt2_arr - np.power(mean, 2)



    # TODO: improve docs
    @staticmethod
    def corr_time(var, nmeasures, acceptprob):
        """Estimate the correlation time in a Markov chain (with rejection).

        Estimates the correlation time using the mean value
        of the product in consecutive steps and the variance
        (it is assumed that the autocorrelation decays
        exponentially).

        Parameters
        ----------
            var : float (scalar or array)
                Variance.

            nmeasure : int (scalar or array)
                Number of measures.

            acceptprob : float (scalar or array)
                Proposal acceptance probability.

        Returns
        -------
            corr_time : float (scalar or array)
            
        """
        return nmeasures*var/(2.*acceptprob)


    @classmethod
    def samplemean_error(cls, mean, momnt2, acceptprob, nmeasures):
        """Calculate the sample mean error in rejection with repetition.

        Parameters
        ----------
            mean : float (scalar or array)
                Sample mean of the calculated magnitued.

            momnt2 : float (scalar or array)
                Sample second raw moment of the magnitude.

            corr1 : float (scalar or array) 
                Product of the magnitude in consecutive 
                steps.

            nmeasures: int (scalar or array)
                Number of measures.

        Returns
        -------
            error : float (scalar or array)
            
        """
        # Calculate the variance
        var = cls.variance(mean, momnt2)

        # If the variance is zero, the error is directly zero.
        # If we use the formula in those cases a zero division is
        # done, so we have to treat the zero values separately.

        # Ensure the data is stored in arrays
        var_arr = var*np.ones(1)
        nmeasures_arr = nmeasures*np.ones(1)
        acceptprob_arr = acceptprob*np.ones(1)
        
        # Create array for the results
        error = np.zeros(var_arr.size, dtype=float)

        # Find the array indexes with nonzero variance and calculate
        # the error in those cases
        nonzero_idxs = np.argwhere(var_arr != 0)
        corrtime = cls.corr_time(
                var_arr[nonzero_idxs], nmeasures_arr[nonzero_idxs],
                acceptprob_arr[nonzero_idxs])
        error[nonzero_idxs] = np.sqrt(
                var_arr[nonzero_idxs]/nmeasures_arr[nonzero_idxs]*(
                2.*corrtime + 1.))

        # If the array size is one, convert it to a scalar
        if error.size == 1:
            error = np.asscalar(error)

        return error

# TODO: make the function check and treat properly measures with 
# the same T but different measure intervals
def mergeresults(results_list):
    """Merge several results objects into one.

    Be careful: right now the function does not treat properly 
    measures with the same temperature but different 
    measure intervals.

    Parameters
    ----------
        results_list : isingmodel.Results list
            List with the Results objects to be merged. All the 
            Results objects in the list bust have the same shape.
            in the list must have the 

    Returns
    -------
        merged: :py:class:`isingmodel.Results` object
            Results object with all the data from results list.
    """
    # Check that all the list elements have the same shape
    shape = results_list[0].shape
    for results in results_list:
        if results.shape != shape:
            raise ValueError(
                    "All the elements in the list must have the same shape")

    # Create the object where all the data will be stored
    merged = Results(shape=shape)

    # Loop over the results objects
    for results in results_list:
        # Loop over the measured temperatures
        for T_idx, T in enumerate(results.Ts):
            # If T is already in merged, average the results
            if T in merged.Ts:
                idx = merged.Ts.index(T) 

                merged.mags[idx] = np.average(
                        [merged.mags[idx], results.mags[T_idx]],
                        weights=[merged.nmeasures[idx], 
                                results.nmeasures[T_idx]])
                merged.mag2s[idx] = np.average(
                        [merged.mag2s[idx], results.mag2s[T_idx]],
                        weights=[merged.nmeasures[idx], 
                                results.nmeasures[T_idx]])
                merged.mag4s[idx] = np.average(
                        [merged.mag4s[idx], results.mag4s[T_idx]],
                        weights=[merged.nmeasures[idx], 
                                results.nmeasures[T_idx]])
                merged.corrs[idx] = np.average(
                        [merged.corrs[idx], results.corrs[T_idx]],
                        weights=[merged.nmeasures[idx], 
                                results.nmeasures[T_idx]])
                merged.acceptprobs[idx] = np.average(
                        [merged.acceptprobs[idx], results.acceptprobs[T_idx]],
                        weights=[merged.nmeasures[idx], 
                                results.nmeasures[T_idx]])
                merged.nmeasures[idx] += results.nmeasures[T_idx]
            # Else, create a new entry for the measures
            else:
                merged.Ts.append(
                        results.Ts[T_idx])
                merged.nmeasures.append(
                        results.nmeasures[T_idx])
                merged.measureintervals.append(
                        results.measureintervals[T_idx])
                merged.mags.append(
                        results.mags[T_idx])
                merged.mag2s.append(
                        results.mag2s[T_idx])
                merged.mag4s.append(
                        results.mag4s[T_idx])
                merged.corrs.append(
                        results.corrs[T_idx])
                merged.acceptprobs.append(
                        results.acceptprobs[T_idx])
    return merged