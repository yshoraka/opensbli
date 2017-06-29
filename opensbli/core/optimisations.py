
from .opensblifunctions import CentralDerivative
from .kernel import *
#from .latex import *
from opensbli.core.scheme import Central
from opensbli.utilities.helperfunctions import increasing_order, decreasing_order
class Store_some_optimisation(Central):
    """Optimisation this wil work as not classifying the derivatives into
    convective and viscous terms
    """
    def __init__(self, order):
        Central.__init__(self, order)
        
        return
    
    def discretise(self, type_of_eq, block):
        pprint(type_of_eq)
        equations =  flatten(type_of_eq.equations)
        residual_arrays = [eq.residual for eq in equations]
        #equations = [e._sanitise_equation for e in equations]
        self.required_constituent_relations = {}
        cds = self.get_local_function(equations)
        grouped = self.group_by_direction(cds)
        
        homogenous_ders, non_homogenous_ders = self.process_group(grouped)
        self.groups_to_a_kernel(homogenous_ders, block)
        return
    def groups_to_a_kernel(self, derivatives, block):
        kernels = dict(zip(derivatives.keys(), [Kernel(block) for k in derivatives.keys()]))
        # Update the work arrays if used else where
        for key, value in derivatives.iteritems():
            for v in value:
                if v.used_else_where:
                    v.update_work(block)
                    block.increase_work_index
        # Store the work index
        block.store_work_index
        for key, value in derivatives.iteritems():
            for v in value:
                if not v.used_else_where:
                    v.update_work(block)
                    block.increase_work_index
                    kernels[key].add_equation(Eq(v.work, v._discretise_derivative(self, block)))
        print block.work_index
        return
    def process_group(self, grouped):
        homogenous_ders = dict(zip(grouped.keys(), [[] for k in grouped.keys()]))
        non_homogenous_ders = dict(zip(grouped.keys(), [[] for k in grouped.keys()]))
        for key in grouped:
            for v in grouped[key]:
                if not v.is_homogeneous:
                    sanitised = v._sanitise
                    sanitised.direction_used = []
                    non_homogenous_ders[key] += [sanitised]
                else:
                    sanitised = v._sanitise
                    sanitised.direction_used = []
                    homogenous_ders[key] += [sanitised]
        #pprint(non_homogenous_ders)
        for key, value in non_homogenous_ders.iteritems():
            for v in value:
                inner = self.find_inner(v)
                for i in inner:
                    i.is_used(True)
                    i.direction_used += v.get_direction
        return homogenous_ders, non_homogenous_ders
    def find_inner(self, CD):
        expr = CD.copy()
        inner_cds = []
        
        pot = postorder_traversal(CD)
        inner_cds = []
        for p in pot:
            if isinstance(p, CentralDerivative):
                inner_cds += [p]
            else:
                continue
        inner_cds = [i for i in inner_cds if i is not CD]
        return inner_cds
    def ssalgorithm(self,equations):
        
        return

class BL_optimisation(Central):
    """Optimisation this wil work as not classifying the derivatives into
    convective and viscous terms
    """
    def __init__(self, order):
        Central.__init__(self, order)
        return

    def discretise(self, type_of_eq, block):
        self.set_halos(block) # THis is important
        equations =  flatten(type_of_eq.equations)
        residual_arrays = [eq.residual for eq in equations]
        equations = [e._sanitise_equation for e in equations]
        rhs_eq = [e.rhs for e in equations]
        self.required_constituent_relations = {}
        #classify_parameter = ConstantObject("Re")
        self.required_constituent_relations = {}
        #viscous, convective = self.classify_equations_on_parameter(equations, classify_parameter)
        #pprint(convective)
        local_kernels, discretised_eq = self.genral_discretisation(rhs_eq, block, name="BL alg")
        #pprint(discretised_eq)
        self.add(local_kernels, discretised_eq, type_of_eq, block)
        if discretised_eq :
            conv_residual_kernel = self.create_residual_kernel(residual_arrays, discretised_eq, block)
            conv_residual_kernel.set_computation_name("Residual ")
            type_of_eq.Kernels += [conv_residual_kernel]
        
        return self.required_constituent_relations
    def add(self, local_kernels, discretised_eq, type_of_eq, block):
        if discretised_eq:
            for ker in sorted(local_kernels, cmp=increasing_order):
                eval_ker = local_kernels[ker]
                #eval_ker.set_computation_name("%s "%(ker))
                #eval_ker.update_block_datasets(block)
                type_of_eq.Kernels += [eval_ker]
        return
    
class RA_optimisation(Central):
    """Optimisation this wil work as not classifying the derivatives into
    convective and viscous terms
    """
    def __init__(self, order):
        Central.__init__(self, order)
        
        return
    
    def discretise(self, type_of_eq, block):
        self.set_halos(block) # THis is important
        pprint(self)
        equations =  flatten(type_of_eq.equations)
        residual_arrays = [eq.residual for eq in equations]
        equations = [e._sanitise_equation for e in equations]
        rhs_eq = [e.rhs for e in equations]
        #print "nhere"
        self.required_constituent_relations = {}
        equations = [Eq(x,y) for x,y in zip(residual_arrays, rhs_eq)]
        discretised_eq = self.RA(equations, block)
        if discretised_eq:
            discretisation_kernel = Kernel(block, computation_name="%s evaluation"%type_of_eq.__class__.__name__)
            discretisation_kernel.set_grid_range(block)
            for eq in discretised_eq:
                discretisation_kernel.add_equation(eq)
            discretisation_kernel.update_block_datasets(block)
            type_of_eq.Kernels +=  [discretisation_kernel]
        return self.required_constituent_relations
    
    def RA(self, equations, block):
        cds = self.get_local_function(equations)
        descritised_equations = equations[:]
        #pprint(cds)
        work_arry_subs = {}
        if cds:
            for der in sorted(cds, cmp=decreasing_order):
                self.update_range_of_constituent_relations(der, block)
                expr = der.copy()
                inner_cds = []
                #if CD.args[0].atoms(CentralDerivative):
                pot = postorder_traversal(expr)
                inner_cds = []
                for p in pot:
                    if isinstance(p, CentralDerivative):
                        inner_cds += [p]
                    else:
                        continue
                # Contains inner derivatives
                if len(inner_cds)>1:
                    for np,cd in enumerate(inner_cds[:-1]):
                        expr = expr.subs(cd, cd._discretise_derivative(self, block))
                expr_discretised = expr._discretise_derivative(self, block)
                
                for no, c in enumerate(descritised_equations):
                    descritised_equations[no] = descritised_equations[no].subs(der, expr_discretised)
            return descritised_equations
        else:
            return None
class SN_optimisation(Central):
    """Optimisation this wil work as not classifying the derivatives into
    convective and viscous terms
    """
    def __init__(self, order):
        Central.__init__(self, order)
        
        return
    
    def discretise(self, type_of_eq, block):
        self.set_halos(block) # THis is important
        pprint(self)
        equations =  flatten(type_of_eq.equations)
        residual_arrays = [eq.residual for eq in equations]
        equations = [e._sanitise_equation for e in equations]
        rhs_eq = [e.rhs for e in equations]
        #print "nhere"
        self.required_constituent_relations = {}
        equations = [Eq(x,y) for x,y in zip(residual_arrays, rhs_eq)]
        discretised_eq = self.SN(equations, block)
        if discretised_eq:
            discretisation_kernel = Kernel(block, computation_name="%s evaluation"%type_of_eq.__class__.__name__)
            discretisation_kernel.set_grid_range(block)
            for eq in discretised_eq:
                discretisation_kernel.add_equation(eq)
            discretisation_kernel.update_block_datasets(block)
            type_of_eq.Kernels +=  [discretisation_kernel]
        return self.required_constituent_relations

    def SN(self, equations, block):
        cds = self.get_local_function(equations)
        descritised_equations = equations[:]
        #pprint(cds)
        work_arry_subs = {}
        local_eq = []
        if cds:
            gvs = [GridVariable("localeval_%d"%i) for i in range(len(cds))]
            for der in sorted(cds, cmp=decreasing_order):
                self.update_range_of_constituent_relations(der, block)
                expr = der.copy()
                inner_cds = []
                #if CD.args[0].atoms(CentralDerivative):
                pot = postorder_traversal(expr)
                inner_cds = []
                for p in pot:
                    if isinstance(p, CentralDerivative):
                        inner_cds += [p]
                    else:
                        continue
                # Contains inner derivatives
                if len(inner_cds)>1:
                    for np,cd in enumerate(inner_cds[:-1]):
                        expr = expr.subs(cd, cd._discretise_derivative(self, block))
                expr_discretised = expr._discretise_derivative(self, block)
                var = gvs.pop(0)
                local_eq += [Eq(var, expr_discretised)]
                for no, c in enumerate(descritised_equations):
                    descritised_equations[no] = descritised_equations[no].subs(der, var)
            # add the local equations to discretised 
            return local_eq + descritised_equations
        else:
            return None

class SN_optimisation_level_2(Central):
    """Optimisation this wil work as not classifying the derivatives into
    convective and viscous terms
    """
    def __init__(self, order):
        Central.__init__(self, order)
        
        return
    
    def discretise(self, type_of_eq, block):
        self.set_halos(block) # THis is important
        pprint(self)
        equations =  flatten(type_of_eq.equations)
        residual_arrays = [eq.residual for eq in equations]
        equations = [e._sanitise_equation for e in equations]
        # Group to convective and viscous terms
        classify_parameter = ConstantObject("Re")
        self.required_constituent_relations = {}
        viscous, convective = self.classify_equations_on_parameter(equations, classify_parameter)
        # First process the convective terms
        equations = [Eq(x,x+y) for x,y in zip(residual_arrays, convective)]
        self.latex = LatexWriter()
        self.latex.open('./discretise.tex')
        metadata = {"title": "Discretise", "author": "Jammy", "institution": ""}
        self.latex.write_header(metadata)
        discretised_eq = self.SN(equations, block)
        if discretised_eq:
            discretisation_kernel = Kernel(block, computation_name="%s Convective evaluation"%type_of_eq.__class__.__name__)
            discretisation_kernel.set_grid_range(block)
            for eq in discretised_eq:
                discretisation_kernel.add_equation(eq)
            discretisation_kernel.update_block_datasets(block)
            type_of_eq.Kernels +=  [discretisation_kernel]
        # The viscous terms
        equations = [Eq(x,x+y) for x,y in zip(residual_arrays, viscous)]
        discretised_eq = self.SN(equations, block)
        if discretised_eq:
            discretisation_kernel = Kernel(block, computation_name="%s Viscous evaluation"%type_of_eq.__class__.__name__)
            discretisation_kernel.set_grid_range(block)
            for eq in discretised_eq:
                discretisation_kernel.add_equation(eq)
            discretisation_kernel.update_block_datasets(block)
            type_of_eq.Kernels +=  [discretisation_kernel]
        self.latex.write_footer()
        self.latex.close()

        return self.required_constituent_relations
    def SN(self, equations, block):
        cds = self.get_local_function(equations)
        descritised_equations = equations[:]
        #pprint(cds)
        work_arry_subs = {}
        local_eq = []
        if cds:
            gvs = [GridVariable("leval_%d"%i) for i in range(len(cds))]
            for der in sorted(cds, cmp=decreasing_order):
                self.update_range_of_constituent_relations(der, block)
                expr = der.copy()
                inner_cds = []
                #if CD.args[0].atoms(CentralDerivative):
                pot = postorder_traversal(expr)
                inner_cds = []
                for p in pot:
                    if isinstance(p, CentralDerivative):
                        inner_cds += [p]
                    else:
                        continue
                # Contains inner derivatives
                if len(inner_cds)>1:
                    for np,cd in enumerate(inner_cds[:-1]):
                        expr = expr.subs(cd, cd._discretise_derivative(self, block))
                expr_discretised = expr._discretise_derivative(self, block)
                var = gvs.pop(0)
                self.latex.write_expression(Eq(der, Eq(var, expr_discretised)))
                local_eq += [Eq(var, expr_discretised)]
                for no, c in enumerate(descritised_equations):
                    descritised_equations[no] = descritised_equations[no].subs(der, var)
            # add the local equations to discretised 
            return local_eq + descritised_equations
        else:
            return None

class RA_optimisation_level_2(Central):
    """Optimisation this wil work as not classifying the derivatives into
    convective and viscous terms
    """
    def __init__(self, order):
        Central.__init__(self, order)
        
        return
    
    def discretise(self, type_of_eq, block):
        self.set_halos(block) # THis is important
        pprint(self)
        equations =  flatten(type_of_eq.equations)
        residual_arrays = [eq.residual for eq in equations]
        equations = [e._sanitise_equation for e in equations]
        classify_parameter = ConstantObject("Re")
        self.required_constituent_relations = {}
        viscous, convective = self.classify_equations_on_parameter(equations, classify_parameter)
        # First process the convective terms
        equations = [Eq(x,x+y) for x,y in zip(residual_arrays, convective)]
        discretised_eq = self.RA(equations, block)
        if discretised_eq:
            discretisation_kernel = Kernel(block, computation_name="%s Convective evaluation"%type_of_eq.__class__.__name__)
            discretisation_kernel.set_grid_range(block)
            for eq in discretised_eq:
                discretisation_kernel.add_equation(eq)
            discretisation_kernel.update_block_datasets(block)
            type_of_eq.Kernels +=  [discretisation_kernel]
        # The viscous terms
        equations = [Eq(x,x+y) for x,y in zip(residual_arrays, viscous)]
        discretised_eq = self.RA(equations, block)
        if discretised_eq:
            discretisation_kernel = Kernel(block, computation_name="%s Viscous evaluation"%type_of_eq.__class__.__name__)
            discretisation_kernel.set_grid_range(block)
            for eq in discretised_eq:
                discretisation_kernel.add_equation(eq)
            discretisation_kernel.update_block_datasets(block)
            type_of_eq.Kernels +=  [discretisation_kernel]
        return self.required_constituent_relations
    
    def RA(self, equations, block):
        cds = self.get_local_function(equations)
        descritised_equations = equations[:]
        #pprint(cds)
        work_arry_subs = {}
        if cds:
            for der in sorted(cds, cmp=decreasing_order):
                self.update_range_of_constituent_relations(der, block)
                expr = der.copy()
                inner_cds = []
                #if CD.args[0].atoms(CentralDerivative):
                pot = postorder_traversal(expr)
                inner_cds = []
                for p in pot:
                    if isinstance(p, CentralDerivative):
                        inner_cds += [p]
                    else:
                        continue
                # Contains inner derivatives
                if len(inner_cds)>1:
                    for np,cd in enumerate(inner_cds[:-1]):
                        expr = expr.subs(cd, cd._discretise_derivative(self, block))
                expr_discretised = expr._discretise_derivative(self, block)
                
                for no, c in enumerate(descritised_equations):
                    descritised_equations[no] = descritised_equations[no].subs(der, expr_discretised)
            return descritised_equations
        else:
            return None




class RA_optimisation_level_3(Central):
    """Optimisation this wil work as not classifying the derivatives into
    convective and viscous terms
    """
    def __init__(self, order):
        Central.__init__(self, order)
        
        return
    
    def discretise(self, type_of_eq, block):
        self.set_halos(block) # THis is important
        pprint(self)
        equations =  flatten(type_of_eq.equations)
        residual_arrays = [eq.residual for eq in equations]
        equations = [e._sanitise_equation for e in equations]
        rhs_eq = [e.rhs for e in equations]
        #print "nhere"
        self.required_constituent_relations = {}
        equations = [Eq(x,y) for x,y in zip(residual_arrays, rhs_eq)]
        discretised_eq = self.RA(equations, block)
        if discretised_eq:
            for no, eq in enumerate(discretised_eq):
                discretisation_kernel = Kernel(block, computation_name="%s evaluation%d"%(type_of_eq.__class__.__name__, no))
                discretisation_kernel.set_grid_range(block)
                discretisation_kernel.add_equation(eq)
                discretisation_kernel.update_block_datasets(block)
                type_of_eq.Kernels +=  [discretisation_kernel]
        return self.required_constituent_relations
    
    def RA(self, equations, block):
        cds = self.get_local_function(equations)
        descritised_equations = equations[:]
        #pprint(cds)
        work_arry_subs = {}
        if cds:
            for der in sorted(cds, cmp=decreasing_order):
                self.update_range_of_constituent_relations(der, block)
                expr = der.copy()
                inner_cds = []
                #if CD.args[0].atoms(CentralDerivative):
                pot = postorder_traversal(expr)
                inner_cds = []
                for p in pot:
                    if isinstance(p, CentralDerivative):
                        inner_cds += [p]
                    else:
                        continue
                # Contains inner derivatives
                if len(inner_cds)>1:
                    for np,cd in enumerate(inner_cds[:-1]):
                        expr = expr.subs(cd, cd._discretise_derivative(self, block))
                expr_discretised = expr._discretise_derivative(self, block)
                
                for no, c in enumerate(descritised_equations):
                    descritised_equations[no] = descritised_equations[no].subs(der, expr_discretised)
            return descritised_equations
        else:
            return None