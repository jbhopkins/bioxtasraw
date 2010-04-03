#ifdef __CPLUSPLUS__
extern "C" {
#endif

#ifndef __GNUC__
#pragma warning(disable: 4275)
#pragma warning(disable: 4101)

#endif
#include "Python.h"
#include "blitz/array.h"
#include "compile.h"
#include "frameobject.h"
#include <complex>
#include <math.h>
#include <string>
#include "scxx/object.h"
#include "scxx/list.h"
#include "scxx/tuple.h"
#include "scxx/dict.h"
#include <iostream>
#include <stdio.h>
#include "numpy/arrayobject.h"




// global None value for use in functions.
namespace py {
object None = object(Py_None);
}

const char* find_type(PyObject* py_obj)
{
    if(py_obj == NULL) return "C NULL value";
    if(PyCallable_Check(py_obj)) return "callable";
    if(PyString_Check(py_obj)) return "string";
    if(PyInt_Check(py_obj)) return "int";
    if(PyFloat_Check(py_obj)) return "float";
    if(PyDict_Check(py_obj)) return "dict";
    if(PyList_Check(py_obj)) return "list";
    if(PyTuple_Check(py_obj)) return "tuple";
    if(PyFile_Check(py_obj)) return "file";
    if(PyModule_Check(py_obj)) return "module";

    //should probably do more intergation (and thinking) on these.
    if(PyCallable_Check(py_obj) && PyInstance_Check(py_obj)) return "callable";
    if(PyInstance_Check(py_obj)) return "instance";
    if(PyCallable_Check(py_obj)) return "callable";
    return "unkown type";
}

void throw_error(PyObject* exc, const char* msg)
{
 //printf("setting python error: %s\n",msg);
  PyErr_SetString(exc, msg);
  //printf("throwing error\n");
  throw 1;
}

void handle_bad_type(PyObject* py_obj, const char* good_type, const char* var_name)
{
    char msg[500];
    sprintf(msg,"received '%s' type instead of '%s' for variable '%s'",
            find_type(py_obj),good_type,var_name);
    throw_error(PyExc_TypeError,msg);
}

void handle_conversion_error(PyObject* py_obj, const char* good_type, const char* var_name)
{
    char msg[500];
    sprintf(msg,"Conversion Error:, received '%s' type instead of '%s' for variable '%s'",
            find_type(py_obj),good_type,var_name);
    throw_error(PyExc_TypeError,msg);
}


class int_handler
{
public:
    int convert_to_int(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        
        if (!py_obj || !PyInt_Check(py_obj))
            handle_conversion_error(py_obj,"int", name);
        return (int) PyInt_AsLong(py_obj);
    }

    int py_to_int(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyInt_Check(py_obj))
            handle_bad_type(py_obj,"int", name);
        
        return (int) PyInt_AsLong(py_obj);
    }
};

int_handler x__int_handler = int_handler();
#define convert_to_int(py_obj,name) \
        x__int_handler.convert_to_int(py_obj,name)
#define py_to_int(py_obj,name) \
        x__int_handler.py_to_int(py_obj,name)


PyObject* int_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class float_handler
{
public:
    double convert_to_float(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        
        if (!py_obj || !PyFloat_Check(py_obj))
            handle_conversion_error(py_obj,"float", name);
        return PyFloat_AsDouble(py_obj);
    }

    double py_to_float(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyFloat_Check(py_obj))
            handle_bad_type(py_obj,"float", name);
        
        return PyFloat_AsDouble(py_obj);
    }
};

float_handler x__float_handler = float_handler();
#define convert_to_float(py_obj,name) \
        x__float_handler.convert_to_float(py_obj,name)
#define py_to_float(py_obj,name) \
        x__float_handler.py_to_float(py_obj,name)


PyObject* float_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class complex_handler
{
public:
    std::complex<double> convert_to_complex(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        
        if (!py_obj || !PyComplex_Check(py_obj))
            handle_conversion_error(py_obj,"complex", name);
        return std::complex<double>(PyComplex_RealAsDouble(py_obj),PyComplex_ImagAsDouble(py_obj));
    }

    std::complex<double> py_to_complex(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyComplex_Check(py_obj))
            handle_bad_type(py_obj,"complex", name);
        
        return std::complex<double>(PyComplex_RealAsDouble(py_obj),PyComplex_ImagAsDouble(py_obj));
    }
};

complex_handler x__complex_handler = complex_handler();
#define convert_to_complex(py_obj,name) \
        x__complex_handler.convert_to_complex(py_obj,name)
#define py_to_complex(py_obj,name) \
        x__complex_handler.py_to_complex(py_obj,name)


PyObject* complex_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class unicode_handler
{
public:
    Py_UNICODE* convert_to_unicode(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        Py_XINCREF(py_obj);
        if (!py_obj || !PyUnicode_Check(py_obj))
            handle_conversion_error(py_obj,"unicode", name);
        return PyUnicode_AS_UNICODE(py_obj);
    }

    Py_UNICODE* py_to_unicode(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyUnicode_Check(py_obj))
            handle_bad_type(py_obj,"unicode", name);
        Py_XINCREF(py_obj);
        return PyUnicode_AS_UNICODE(py_obj);
    }
};

unicode_handler x__unicode_handler = unicode_handler();
#define convert_to_unicode(py_obj,name) \
        x__unicode_handler.convert_to_unicode(py_obj,name)
#define py_to_unicode(py_obj,name) \
        x__unicode_handler.py_to_unicode(py_obj,name)


PyObject* unicode_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class string_handler
{
public:
    std::string convert_to_string(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        Py_XINCREF(py_obj);
        if (!py_obj || !PyString_Check(py_obj))
            handle_conversion_error(py_obj,"string", name);
        return std::string(PyString_AsString(py_obj));
    }

    std::string py_to_string(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyString_Check(py_obj))
            handle_bad_type(py_obj,"string", name);
        Py_XINCREF(py_obj);
        return std::string(PyString_AsString(py_obj));
    }
};

string_handler x__string_handler = string_handler();
#define convert_to_string(py_obj,name) \
        x__string_handler.convert_to_string(py_obj,name)
#define py_to_string(py_obj,name) \
        x__string_handler.py_to_string(py_obj,name)


               PyObject* string_to_py(std::string s)
               {
                   return PyString_FromString(s.c_str());
               }
               
class list_handler
{
public:
    py::list convert_to_list(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        
        if (!py_obj || !PyList_Check(py_obj))
            handle_conversion_error(py_obj,"list", name);
        return py::list(py_obj);
    }

    py::list py_to_list(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyList_Check(py_obj))
            handle_bad_type(py_obj,"list", name);
        
        return py::list(py_obj);
    }
};

list_handler x__list_handler = list_handler();
#define convert_to_list(py_obj,name) \
        x__list_handler.convert_to_list(py_obj,name)
#define py_to_list(py_obj,name) \
        x__list_handler.py_to_list(py_obj,name)


PyObject* list_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class dict_handler
{
public:
    py::dict convert_to_dict(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        
        if (!py_obj || !PyDict_Check(py_obj))
            handle_conversion_error(py_obj,"dict", name);
        return py::dict(py_obj);
    }

    py::dict py_to_dict(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyDict_Check(py_obj))
            handle_bad_type(py_obj,"dict", name);
        
        return py::dict(py_obj);
    }
};

dict_handler x__dict_handler = dict_handler();
#define convert_to_dict(py_obj,name) \
        x__dict_handler.convert_to_dict(py_obj,name)
#define py_to_dict(py_obj,name) \
        x__dict_handler.py_to_dict(py_obj,name)


PyObject* dict_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class tuple_handler
{
public:
    py::tuple convert_to_tuple(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        
        if (!py_obj || !PyTuple_Check(py_obj))
            handle_conversion_error(py_obj,"tuple", name);
        return py::tuple(py_obj);
    }

    py::tuple py_to_tuple(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyTuple_Check(py_obj))
            handle_bad_type(py_obj,"tuple", name);
        
        return py::tuple(py_obj);
    }
};

tuple_handler x__tuple_handler = tuple_handler();
#define convert_to_tuple(py_obj,name) \
        x__tuple_handler.convert_to_tuple(py_obj,name)
#define py_to_tuple(py_obj,name) \
        x__tuple_handler.py_to_tuple(py_obj,name)


PyObject* tuple_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class file_handler
{
public:
    FILE* convert_to_file(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        Py_XINCREF(py_obj);
        if (!py_obj || !PyFile_Check(py_obj))
            handle_conversion_error(py_obj,"file", name);
        return PyFile_AsFile(py_obj);
    }

    FILE* py_to_file(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyFile_Check(py_obj))
            handle_bad_type(py_obj,"file", name);
        Py_XINCREF(py_obj);
        return PyFile_AsFile(py_obj);
    }
};

file_handler x__file_handler = file_handler();
#define convert_to_file(py_obj,name) \
        x__file_handler.convert_to_file(py_obj,name)
#define py_to_file(py_obj,name) \
        x__file_handler.py_to_file(py_obj,name)


               PyObject* file_to_py(FILE* file, char* name, char* mode)
               {
                   return (PyObject*) PyFile_FromFile(file, name, mode, fclose);
               }
               
class instance_handler
{
public:
    py::object convert_to_instance(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        
        if (!py_obj || !PyInstance_Check(py_obj))
            handle_conversion_error(py_obj,"instance", name);
        return py::object(py_obj);
    }

    py::object py_to_instance(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyInstance_Check(py_obj))
            handle_bad_type(py_obj,"instance", name);
        
        return py::object(py_obj);
    }
};

instance_handler x__instance_handler = instance_handler();
#define convert_to_instance(py_obj,name) \
        x__instance_handler.convert_to_instance(py_obj,name)
#define py_to_instance(py_obj,name) \
        x__instance_handler.py_to_instance(py_obj,name)


PyObject* instance_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class numpy_size_handler
{
public:
    void conversion_numpy_check_size(PyArrayObject* arr_obj, int Ndims,
                                     const char* name)
    {
        if (arr_obj->nd != Ndims)
        {
            char msg[500];
            sprintf(msg,"Conversion Error: received '%d' dimensional array instead of '%d' dimensional array for variable '%s'",
                    arr_obj->nd,Ndims,name);
            throw_error(PyExc_TypeError,msg);
        }
    }

    void numpy_check_size(PyArrayObject* arr_obj, int Ndims, const char* name)
    {
        if (arr_obj->nd != Ndims)
        {
            char msg[500];
            sprintf(msg,"received '%d' dimensional array instead of '%d' dimensional array for variable '%s'",
                    arr_obj->nd,Ndims,name);
            throw_error(PyExc_TypeError,msg);
        }
    }
};

numpy_size_handler x__numpy_size_handler = numpy_size_handler();
#define conversion_numpy_check_size x__numpy_size_handler.conversion_numpy_check_size
#define numpy_check_size x__numpy_size_handler.numpy_check_size


class numpy_type_handler
{
public:
    void conversion_numpy_check_type(PyArrayObject* arr_obj, int numeric_type,
                                     const char* name)
    {
        // Make sure input has correct numeric type.
        int arr_type = arr_obj->descr->type_num;
        if (PyTypeNum_ISEXTENDED(numeric_type))
        {
        char msg[80];
        sprintf(msg, "Conversion Error: extended types not supported for variable '%s'",
                name);
        throw_error(PyExc_TypeError, msg);
        }
        if (!PyArray_EquivTypenums(arr_type, numeric_type))
        {

        const char* type_names[23] = {"bool", "byte", "ubyte","short", "ushort",
                                "int", "uint", "long", "ulong", "longlong", "ulonglong",
                                "float", "double", "longdouble", "cfloat", "cdouble",
                                "clongdouble", "object", "string", "unicode", "void", "ntype",
                                "unknown"};
        char msg[500];
        sprintf(msg,"Conversion Error: received '%s' typed array instead of '%s' typed array for variable '%s'",
                type_names[arr_type],type_names[numeric_type],name);
        throw_error(PyExc_TypeError,msg);
        }
    }

    void numpy_check_type(PyArrayObject* arr_obj, int numeric_type, const char* name)
    {
        // Make sure input has correct numeric type.
        int arr_type = arr_obj->descr->type_num;
        if (PyTypeNum_ISEXTENDED(numeric_type))
        {
        char msg[80];
        sprintf(msg, "Conversion Error: extended types not supported for variable '%s'",
                name);
        throw_error(PyExc_TypeError, msg);
        }
        if (!PyArray_EquivTypenums(arr_type, numeric_type))
        {
            const char* type_names[23] = {"bool", "byte", "ubyte","short", "ushort",
                                    "int", "uint", "long", "ulong", "longlong", "ulonglong",
                                    "float", "double", "longdouble", "cfloat", "cdouble",
                                    "clongdouble", "object", "string", "unicode", "void", "ntype",
                                    "unknown"};
            char msg[500];
            sprintf(msg,"received '%s' typed array instead of '%s' typed array for variable '%s'",
                    type_names[arr_type],type_names[numeric_type],name);
            throw_error(PyExc_TypeError,msg);
        }
    }
};

numpy_type_handler x__numpy_type_handler = numpy_type_handler();
#define conversion_numpy_check_type x__numpy_type_handler.conversion_numpy_check_type
#define numpy_check_type x__numpy_type_handler.numpy_check_type


class numpy_handler
{
public:
    PyArrayObject* convert_to_numpy(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        Py_XINCREF(py_obj);
        if (!py_obj || !PyArray_Check(py_obj))
            handle_conversion_error(py_obj,"numpy", name);
        return (PyArrayObject*) py_obj;
    }

    PyArrayObject* py_to_numpy(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !PyArray_Check(py_obj))
            handle_bad_type(py_obj,"numpy", name);
        Py_XINCREF(py_obj);
        return (PyArrayObject*) py_obj;
    }
};

numpy_handler x__numpy_handler = numpy_handler();
#define convert_to_numpy(py_obj,name) \
        x__numpy_handler.convert_to_numpy(py_obj,name)
#define py_to_numpy(py_obj,name) \
        x__numpy_handler.py_to_numpy(py_obj,name)


PyObject* numpy_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}


class catchall_handler
{
public:
    py::object convert_to_catchall(PyObject* py_obj, const char* name)
    {
        // Incref occurs even if conversion fails so that
        // the decref in cleanup_code has a matching incref.
        
        if (!py_obj || !(py_obj))
            handle_conversion_error(py_obj,"catchall", name);
        return py::object(py_obj);
    }

    py::object py_to_catchall(PyObject* py_obj, const char* name)
    {
        // !! Pretty sure INCREF should only be called on success since
        // !! py_to_xxx is used by the user -- not the code generator.
        if (!py_obj || !(py_obj))
            handle_bad_type(py_obj,"catchall", name);
        
        return py::object(py_obj);
    }
};

catchall_handler x__catchall_handler = catchall_handler();
#define convert_to_catchall(py_obj,name) \
        x__catchall_handler.convert_to_catchall(py_obj,name)
#define py_to_catchall(py_obj,name) \
        x__catchall_handler.py_to_catchall(py_obj,name)


PyObject* catchall_to_py(PyObject* obj)
{
    return (PyObject*) obj;
}



// This should be declared only if they are used by some function
// to keep from generating needless warnings. for now, we'll always
// declare them.

int _beg = blitz::fromStart;
int _end = blitz::toEnd;
blitz::Range _all = blitz::Range::all();

template<class T, int N>
static blitz::Array<T,N> convert_to_blitz(PyArrayObject* arr_obj,const char* name)
{
    blitz::TinyVector<int,N> shape(0);
    blitz::TinyVector<int,N> strides(0);
    //for (int i = N-1; i >=0; i--)
    for (int i = 0; i < N; i++)
    {
        shape[i] = arr_obj->dimensions[i];
        strides[i] = arr_obj->strides[i]/sizeof(T);
    }
    //return blitz::Array<T,N>((T*) arr_obj->data,shape,
    return blitz::Array<T,N>((T*) arr_obj->data,shape,strides,
                             blitz::neverDeleteData);
}

template<class T, int N>
static blitz::Array<T,N> py_to_blitz(PyArrayObject* arr_obj,const char* name)
{

    blitz::TinyVector<int,N> shape(0);
    blitz::TinyVector<int,N> strides(0);
    //for (int i = N-1; i >=0; i--)
    for (int i = 0; i < N; i++)
    {
        shape[i] = arr_obj->dimensions[i];
        strides[i] = arr_obj->strides[i]/sizeof(T);
    }
    //return blitz::Array<T,N>((T*) arr_obj->data,shape,
    return blitz::Array<T,N>((T*) arr_obj->data,shape,strides,
                             blitz::neverDeleteData);
}


static PyObject* bift(PyObject*self, PyObject* args, PyObject* kywds)
{
    py::object return_val;
    int exception_occured = 0;
    PyObject *py_local_dict = NULL;
    static char *kwlist[] = {"dotsp","dotsptol","maxit","minit","bkkmax","omega","omegamin","omegareduction","B","N","m","P","Psumi","Bmat","alpha","sum_dia","bkk","dP","Pold","local_dict", NULL};
    PyObject *py_dotsp, *py_dotsptol, *py_maxit, *py_minit, *py_bkkmax, *py_omega, *py_omegamin, *py_omegareduction, *py_B, *py_N, *py_m, *py_P, *py_Psumi, *py_Bmat, *py_alpha, *py_sum_dia, *py_bkk, *py_dP, *py_Pold;
    int dotsp_used, dotsptol_used, maxit_used, minit_used, bkkmax_used, omega_used, omegamin_used, omegareduction_used, B_used, N_used, m_used, P_used, Psumi_used, Bmat_used, alpha_used, sum_dia_used, bkk_used, dP_used, Pold_used;
    py_dotsp = py_dotsptol = py_maxit = py_minit = py_bkkmax = py_omega = py_omegamin = py_omegareduction = py_B = py_N = py_m = py_P = py_Psumi = py_Bmat = py_alpha = py_sum_dia = py_bkk = py_dP = py_Pold = NULL;
    dotsp_used= dotsptol_used= maxit_used= minit_used= bkkmax_used= omega_used= omegamin_used= omegareduction_used= B_used= N_used= m_used= P_used= Psumi_used= Bmat_used= alpha_used= sum_dia_used= bkk_used= dP_used= Pold_used = 0;
    
    if(!PyArg_ParseTupleAndKeywords(args,kywds,"OOOOOOOOOOOOOOOOOOO|O:bift",kwlist,&py_dotsp, &py_dotsptol, &py_maxit, &py_minit, &py_bkkmax, &py_omega, &py_omegamin, &py_omegareduction, &py_B, &py_N, &py_m, &py_P, &py_Psumi, &py_Bmat, &py_alpha, &py_sum_dia, &py_bkk, &py_dP, &py_Pold, &py_local_dict))
       return NULL;
    try                              
    {                                
        py_dotsp = py_dotsp;
        double dotsp = convert_to_float(py_dotsp,"dotsp");
        dotsp_used = 1;
        py_dotsptol = py_dotsptol;
        double dotsptol = convert_to_float(py_dotsptol,"dotsptol");
        dotsptol_used = 1;
        py_maxit = py_maxit;
        int maxit = convert_to_int(py_maxit,"maxit");
        maxit_used = 1;
        py_minit = py_minit;
        int minit = convert_to_int(py_minit,"minit");
        minit_used = 1;
        py_bkkmax = py_bkkmax;
        py::object bkkmax = convert_to_catchall(py_bkkmax,"bkkmax");
        bkkmax_used = 1;
        py_omega = py_omega;
        double omega = convert_to_float(py_omega,"omega");
        omega_used = 1;
        py_omegamin = py_omegamin;
        double omegamin = convert_to_float(py_omegamin,"omegamin");
        omegamin_used = 1;
        py_omegareduction = py_omegareduction;
        double omegareduction = convert_to_float(py_omegareduction,"omegareduction");
        omegareduction_used = 1;
        py_B = py_B;
        PyArrayObject* B_array = convert_to_numpy(py_B,"B");
        conversion_numpy_check_type(B_array,PyArray_DOUBLE,"B");
        conversion_numpy_check_size(B_array,2,"B");
        blitz::Array<double,2> B = convert_to_blitz<double,2>(B_array,"B");
        blitz::TinyVector<int,2> NB = B.shape();
        B_used = 1;
        py_N = py_N;
        int N = convert_to_int(py_N,"N");
        N_used = 1;
        py_m = py_m;
        PyArrayObject* m_array = convert_to_numpy(py_m,"m");
        conversion_numpy_check_type(m_array,PyArray_DOUBLE,"m");
        conversion_numpy_check_size(m_array,2,"m");
        blitz::Array<double,2> m = convert_to_blitz<double,2>(m_array,"m");
        blitz::TinyVector<int,2> Nm = m.shape();
        m_used = 1;
        py_P = py_P;
        PyArrayObject* P_array = convert_to_numpy(py_P,"P");
        conversion_numpy_check_type(P_array,PyArray_DOUBLE,"P");
        conversion_numpy_check_size(P_array,2,"P");
        blitz::Array<double,2> P = convert_to_blitz<double,2>(P_array,"P");
        blitz::TinyVector<int,2> NP = P.shape();
        P_used = 1;
        py_Psumi = py_Psumi;
        PyArrayObject* Psumi_array = convert_to_numpy(py_Psumi,"Psumi");
        conversion_numpy_check_type(Psumi_array,PyArray_DOUBLE,"Psumi");
        conversion_numpy_check_size(Psumi_array,2,"Psumi");
        blitz::Array<double,2> Psumi = convert_to_blitz<double,2>(Psumi_array,"Psumi");
        blitz::TinyVector<int,2> NPsumi = Psumi.shape();
        Psumi_used = 1;
        py_Bmat = py_Bmat;
        PyArrayObject* Bmat_array = convert_to_numpy(py_Bmat,"Bmat");
        conversion_numpy_check_type(Bmat_array,PyArray_DOUBLE,"Bmat");
        conversion_numpy_check_size(Bmat_array,2,"Bmat");
        blitz::Array<double,2> Bmat = convert_to_blitz<double,2>(Bmat_array,"Bmat");
        blitz::TinyVector<int,2> NBmat = Bmat.shape();
        Bmat_used = 1;
        py_alpha = py_alpha;
        double alpha = convert_to_float(py_alpha,"alpha");
        alpha_used = 1;
        py_sum_dia = py_sum_dia;
        PyArrayObject* sum_dia_array = convert_to_numpy(py_sum_dia,"sum_dia");
        conversion_numpy_check_type(sum_dia_array,PyArray_DOUBLE,"sum_dia");
        conversion_numpy_check_size(sum_dia_array,2,"sum_dia");
        blitz::Array<double,2> sum_dia = convert_to_blitz<double,2>(sum_dia_array,"sum_dia");
        blitz::TinyVector<int,2> Nsum_dia = sum_dia.shape();
        sum_dia_used = 1;
        py_bkk = py_bkk;
        PyArrayObject* bkk_array = convert_to_numpy(py_bkk,"bkk");
        conversion_numpy_check_type(bkk_array,PyArray_DOUBLE,"bkk");
        conversion_numpy_check_size(bkk_array,2,"bkk");
        blitz::Array<double,2> bkk = convert_to_blitz<double,2>(bkk_array,"bkk");
        blitz::TinyVector<int,2> Nbkk = bkk.shape();
        bkk_used = 1;
        py_dP = py_dP;
        PyArrayObject* dP_array = convert_to_numpy(py_dP,"dP");
        conversion_numpy_check_type(dP_array,PyArray_DOUBLE,"dP");
        conversion_numpy_check_size(dP_array,2,"dP");
        blitz::Array<double,2> dP = convert_to_blitz<double,2>(dP_array,"dP");
        blitz::TinyVector<int,2> NdP = dP.shape();
        dP_used = 1;
        py_Pold = py_Pold;
        PyArrayObject* Pold_array = convert_to_numpy(py_Pold,"Pold");
        conversion_numpy_check_type(Pold_array,PyArray_DOUBLE,"Pold");
        conversion_numpy_check_size(Pold_array,2,"Pold");
        blitz::Array<double,2> Pold = convert_to_blitz<double,2>(Pold_array,"Pold");
        blitz::TinyVector<int,2> NPold = Pold.shape();
        Pold_used = 1;
        /*<function call here>*/     
        
            //#include <iostream.h>
            //#include <math.h>
          
            py::object sout;
            
            // Initiate Variables
            int ite = 0;
          
            double s = 0,
                  wgrads = 0,
                  wgradc = 0,
                  gradci = 0,
                  gradsi = 0;
        
            while( ite < maxit && omega > omegamin && fabs(1-dotsp) > dotsptol || (ite < minit) )
            {
                    if (ite != 0)
                    {
                        /* Calculating smoothness constraint vector m */
                    
                        for(int k = 1; k < N-1; k++)
                        {
                             m(0, k) =  ((P(0,k-1) + P(0,k+1)) / 2.0);
                        }
                        
                        m(0,0) =  P(0,1) / 2.0;
                        m(0,N-1) =  P(0,N-2) /2.0;
                        
           
                        /* This calculates the Matrix Psumi */
                        
                        for(int j = 0; j < N; j++)
                            for(int k = 0; k < N; k++)
                                Psumi(0,j) = Psumi(0,j) + P(0,k) * Bmat(k,j);
            
                       // cout << "    " << Psumi(0,50);
            
                       /* Now calculating dP, and updating P */
                
                        for(int k = 0; k < N; k++)
                        {        
                            dP(0,k) = ( m(0,k) * alpha + sum_dia(0,k) - Psumi(0,k) ) / (bkk(0,k) + alpha);      /* ATTENTION! remember C division!, if its all int's then it will be a int result! .. maybe cast it to float()? */
                            
                            Psumi(0,k) = 0;    // Reset values in Psumi for next iteration..otherwise Psumi = Psumi + blah will be wrong!
                
                            Pold(0,k) = P(0,k);
                 
                            P(0,k) = (1-omega) * P(0,k) + omega * dP(0,k);
                            
                            /* Pin first and last point to zero! */
            
                            //P(0,0) = 0.0;
                            //P(0,N-1) = 0.0;
                        }    
              
                        //cout << "    " << m(0,50);
                        //cout << "    " << P(0,50);
                        //cout << "    " << dP(0,50);
                        //cout << " | ";
                
                    } // end if ite != 0
                
               ite = ite + 1;
            
               /* Calculating Dotsp */
              
               dotsp = 0;
               wgrads = 0;
               wgradc = 0;
               s = 0;
               for(int k = 0; k < N; k++)
               {
                     s = s - pow( P(0,k) - m(0,k) , 2);                        // sum(-power((P-m),2))
                     
                     gradsi = -2*( P(0,k) - m(0,k) );                            // gradsi = (-2*(P-m))
                     wgrads = wgrads + pow(gradsi, 2);
               
                     gradci = 0;
                     for(int j = 0; j < N; j++)
                     {
                         gradci = gradci + 2*( P(0,j) * B(j,k) );     
                     }
                     gradci = gradci - 2*sum_dia(0,k);
                    
                     wgradc = wgradc + pow(gradci , 2);
                     dotsp = dotsp + (gradci * gradsi);
               }
              
        //      cout << dotsp;
        //      cout << "    " << wgrads;
        //      cout << "    " << wgradc;
        //      cout << "    " << s;
        //      cout << " | ";
          
          
               /* internal loop to reduce search step (omega) when it's too large */
                 
               while( dotsp < 0 && double(alpha) < double(bkkmax) && ite > 1 && omega > omegamin)
               {
                        omega = omega / omegareduction;
                        
                        /* Updating P */
                         
                        for(int k = 0; k < N; k++)
                        {
                            P(0,k) = (1-omega) * Pold(0,k) + omega * dP(0,k);
                        }
                        
                        /* Calculating Dotsp */
                        
                        dotsp = 0;
                        wgrads = 0;
                        wgradc = 0;
                        s = 0;
                        for(int k = 0; k < N; k++)
                        {
                            s = s - pow( P(0,k)-m(0,k) , 2);                        // sum(-power((P-m),2))     
                            gradsi = -2*(P(0,k)-m(0,k));                            // gradsi = (-2*(P-m))
                            wgrads = wgrads + pow(gradsi, 2);
                    
                            gradci = 0;
                            for(int j = 0; j < N; j++)
                            {
                                gradci = gradci + 2*( P(0,j) * B(j,k));     
                            }
                            gradci = gradci - 2*sum_dia(0,k);
                              
                            wgradc = wgradc + pow(gradci , 2);
                            dotsp = dotsp + (gradci * gradsi);
                        }    
                        
               } // end inner whileloop
             
                
               if(wgrads == 0 || wgradc == 0)
               {
                    dotsp = 1;
               }
               else
               {
                    wgrads = std::sqrt(wgrads);
                    wgradc = std::sqrt(wgradc);
                    dotsp = dotsp / (wgrads * wgradc);
               }
             
                  
            } // end Outer while loop
            
            
            // cout << "ite C: " << ite;
            // cout << "alpha: " << double(alpha);
            // cout << "omega: " << omega;
            //cout << ",   m: " << m(0,20);
            //cout << ",   dotsp C: " << dotsp;
            //cout << ",   dP:" << dP(0,20);
            //cout << "cnt:" << cnt;
            //cout << ",   wgrads C: " << wgrads;
            //cout << ",   wgradc C: " << wgradc;
            
            
            //tst(0,1) = wgradc;
            sout = s;
            return_val = sout;
        if(py_local_dict)                                  
        {                                                  
            py::dict local_dict = py::dict(py_local_dict); 
        }                                                  
    
    }                                
    catch(...)                       
    {                                
        return_val =  py::object();      
        exception_occured = 1;       
    }                                
    /*cleanup code*/                     
    if(B_used)
    {
        Py_XDECREF(py_B);
    }
    if(m_used)
    {
        Py_XDECREF(py_m);
    }
    if(P_used)
    {
        Py_XDECREF(py_P);
    }
    if(Psumi_used)
    {
        Py_XDECREF(py_Psumi);
    }
    if(Bmat_used)
    {
        Py_XDECREF(py_Bmat);
    }
    if(sum_dia_used)
    {
        Py_XDECREF(py_sum_dia);
    }
    if(bkk_used)
    {
        Py_XDECREF(py_bkk);
    }
    if(dP_used)
    {
        Py_XDECREF(py_dP);
    }
    if(Pold_used)
    {
        Py_XDECREF(py_Pold);
    }
    if(!(PyObject*)return_val && !exception_occured)
    {
                                  
        return_val = Py_None;            
    }
                                  
    return return_val.disown();           
}                                


static PyMethodDef compiled_methods[] = 
{
    {"bift",(PyCFunction)bift , METH_VARARGS|METH_KEYWORDS},
    {NULL,      NULL}        /* Sentinel */
};

PyMODINIT_FUNC initbift_ext(void)
{
    
    Py_Initialize();
    import_array();
    PyImport_ImportModule("numpy");
    (void) Py_InitModule("bift_ext", compiled_methods);
}

#ifdef __CPLUSCPLUS__
}
#endif
