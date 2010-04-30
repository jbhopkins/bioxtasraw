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


               PyObject* file_to_py(FILE* file, const char* name,
                                    const char* mode)
               {
                   return (PyObject*) PyFile_FromFile(file,
                     const_cast<char*>(name),
                     const_cast<char*>(mode), fclose);
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


static PyObject* ravg(PyObject*self, PyObject* args, PyObject* kywds)
{
    py::object return_val;
    int exception_occured = 0;
    PyObject *py_local_dict = NULL;
    static const char *kwlist[] = {"readoutNoiseFound","readoutN","readoutNoise_mask","xlen","ylen","x_c","y_c","hist","low_q","high_q","in_image","hist_count","mask","local_dict", NULL};
    PyObject *py_readoutNoiseFound, *py_readoutN, *py_readoutNoise_mask, *py_xlen, *py_ylen, *py_x_c, *py_y_c, *py_hist, *py_low_q, *py_high_q, *py_in_image, *py_hist_count, *py_mask;
    int readoutNoiseFound_used, readoutN_used, readoutNoise_mask_used, xlen_used, ylen_used, x_c_used, y_c_used, hist_used, low_q_used, high_q_used, in_image_used, hist_count_used, mask_used;
    py_readoutNoiseFound = py_readoutN = py_readoutNoise_mask = py_xlen = py_ylen = py_x_c = py_y_c = py_hist = py_low_q = py_high_q = py_in_image = py_hist_count = py_mask = NULL;
    readoutNoiseFound_used= readoutN_used= readoutNoise_mask_used= xlen_used= ylen_used= x_c_used= y_c_used= hist_used= low_q_used= high_q_used= in_image_used= hist_count_used= mask_used = 0;
    
    if(!PyArg_ParseTupleAndKeywords(args,kywds,"OOOOOOOOOOOOO|O:ravg",const_cast<char**>(kwlist),&py_readoutNoiseFound, &py_readoutN, &py_readoutNoise_mask, &py_xlen, &py_ylen, &py_x_c, &py_y_c, &py_hist, &py_low_q, &py_high_q, &py_in_image, &py_hist_count, &py_mask, &py_local_dict))
       return NULL;
    try                              
    {                                
        py_readoutNoiseFound = py_readoutNoiseFound;
        int readoutNoiseFound = convert_to_int(py_readoutNoiseFound,"readoutNoiseFound");
        readoutNoiseFound_used = 1;
        py_readoutN = py_readoutN;
        PyArrayObject* readoutN_array = convert_to_numpy(py_readoutN,"readoutN");
        conversion_numpy_check_type(readoutN_array,PyArray_DOUBLE,"readoutN");
        conversion_numpy_check_size(readoutN_array,2,"readoutN");
        blitz::Array<double,2> readoutN = convert_to_blitz<double,2>(readoutN_array,"readoutN");
        blitz::TinyVector<int,2> NreadoutN = readoutN.shape();
        readoutN_used = 1;
        py_readoutNoise_mask = py_readoutNoise_mask;
        PyArrayObject* readoutNoise_mask_array = convert_to_numpy(py_readoutNoise_mask,"readoutNoise_mask");
        conversion_numpy_check_type(readoutNoise_mask_array,PyArray_DOUBLE,"readoutNoise_mask");
        conversion_numpy_check_size(readoutNoise_mask_array,2,"readoutNoise_mask");
        blitz::Array<double,2> readoutNoise_mask = convert_to_blitz<double,2>(readoutNoise_mask_array,"readoutNoise_mask");
        blitz::TinyVector<int,2> NreadoutNoise_mask = readoutNoise_mask.shape();
        readoutNoise_mask_used = 1;
        py_xlen = py_xlen;
        int xlen = convert_to_int(py_xlen,"xlen");
        xlen_used = 1;
        py_ylen = py_ylen;
        int ylen = convert_to_int(py_ylen,"ylen");
        ylen_used = 1;
        py_x_c = py_x_c;
        double x_c = convert_to_float(py_x_c,"x_c");
        x_c_used = 1;
        py_y_c = py_y_c;
        double y_c = convert_to_float(py_y_c,"y_c");
        y_c_used = 1;
        py_hist = py_hist;
        PyArrayObject* hist_array = convert_to_numpy(py_hist,"hist");
        conversion_numpy_check_type(hist_array,PyArray_DOUBLE,"hist");
        conversion_numpy_check_size(hist_array,1,"hist");
        blitz::Array<double,1> hist = convert_to_blitz<double,1>(hist_array,"hist");
        blitz::TinyVector<int,1> Nhist = hist.shape();
        hist_used = 1;
        py_low_q = py_low_q;
        int low_q = convert_to_int(py_low_q,"low_q");
        low_q_used = 1;
        py_high_q = py_high_q;
        int high_q = convert_to_int(py_high_q,"high_q");
        high_q_used = 1;
        py_in_image = py_in_image;
        PyArrayObject* in_image_array = convert_to_numpy(py_in_image,"in_image");
        conversion_numpy_check_type(in_image_array,PyArray_DOUBLE,"in_image");
        conversion_numpy_check_size(in_image_array,2,"in_image");
        blitz::Array<double,2> in_image = convert_to_blitz<double,2>(in_image_array,"in_image");
        blitz::TinyVector<int,2> Nin_image = in_image.shape();
        in_image_used = 1;
        py_hist_count = py_hist_count;
        PyArrayObject* hist_count_array = convert_to_numpy(py_hist_count,"hist_count");
        conversion_numpy_check_type(hist_count_array,PyArray_DOUBLE,"hist_count");
        conversion_numpy_check_size(hist_count_array,2,"hist_count");
        blitz::Array<double,2> hist_count = convert_to_blitz<double,2>(hist_count_array,"hist_count");
        blitz::TinyVector<int,2> Nhist_count = hist_count.shape();
        hist_count_used = 1;
        py_mask = py_mask;
        PyArrayObject* mask_array = convert_to_numpy(py_mask,"mask");
        conversion_numpy_check_type(mask_array,PyArray_DOUBLE,"mask");
        conversion_numpy_check_size(mask_array,2,"mask");
        blitz::Array<double,2> mask = convert_to_blitz<double,2>(mask_array,"mask");
        blitz::TinyVector<int,2> Nmask = mask.shape();
        mask_used = 1;
        /*<function call here>*/     
        
            
            double rel_x, rel_y, r, delta, deltaN;
            int x, y;
            //int idx;
             
            for( x = 0; x < xlen; x++)
                   for( y = 0; y < ylen; y++)
                   {
                        rel_x = x-x_c;
                        rel_y = y_c-y;
                   
                        r = int(std::sqrt((rel_y*rel_y) + (rel_x*rel_x)));
                        
                        //res(x,y) = r;
            
                        if( r < high_q && r > low_q && mask(x,y) == 1 && in_image(x,y) > 0)
                        {
                            /* res2(x,y) = r; */               /*  A test image, gives the included range image */
                            
                            hist(r) = hist(r) + in_image(x,y);                   /* Integration of pixel values */
                            
                            hist_count(0, int(r)) = hist_count(0, int(r)) + 1;     /* Number of pixels in a bin */
                            
                            delta = in_image(x,y) - hist_count(1, int(r));         /* Calculation of variance */
                            hist_count(1, int(r)) = hist_count(1, int(r)) + (delta / hist_count(0, int(r)));              
                            hist_count(2, int(r)) = hist_count(2, int(r)) + (delta * (in_image(x,y)-hist_count(1, int(r))));   
                        
                        }
                        
                        if ( readoutNoiseFound == 1 && r < high_q-1 && r > low_q && readoutNoise_mask(x,y) == 0)
                        {
                            
                            readoutN(0,0) = readoutN(0,0) + 1;
                            readoutN(0,1) = readoutN(0,1) + in_image(x,y);
                            
                            deltaN = in_image(x,y) - readoutN(0,2);
                            readoutN(0,2) = readoutN(0,2) + (deltaN / readoutN(0,0));
                            readoutN(0,3) = readoutN(0,3) + (deltaN * (in_image(x,y)-readoutN(0,2)));        
                            
                        }
                    
                    }
            
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
    if(readoutN_used)
    {
        Py_XDECREF(py_readoutN);
    }
    if(readoutNoise_mask_used)
    {
        Py_XDECREF(py_readoutNoise_mask);
    }
    if(hist_used)
    {
        Py_XDECREF(py_hist);
    }
    if(in_image_used)
    {
        Py_XDECREF(py_in_image);
    }
    if(hist_count_used)
    {
        Py_XDECREF(py_hist_count);
    }
    if(mask_used)
    {
        Py_XDECREF(py_mask);
    }
    if(!(PyObject*)return_val && !exception_occured)
    {
                                  
        return_val = Py_None;            
    }
                                  
    return return_val.disown();           
}                                


static PyMethodDef compiled_methods[] = 
{
    {"ravg",(PyCFunction)ravg , METH_VARARGS|METH_KEYWORDS},
    {NULL,      NULL}        /* Sentinel */
};

PyMODINIT_FUNC initravg_ext(void)
{
    
    Py_Initialize();
    import_array();
    PyImport_ImportModule("numpy");
    (void) Py_InitModule("ravg_ext", compiled_methods);
}

#ifdef __CPLUSCPLUS__
}
#endif
