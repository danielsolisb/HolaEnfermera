from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Service, Medication, ServiceCategory, MedicationDoseStep
from .forms import ServiceForm, MedicationForm, CategoryForm, MedicationDoseStepFormSet
from django.db import transaction
from django.db.models import ProtectedError

# --- MIXIN DE SEGURIDAD ---
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.rol in ['ADMINISTRADOR', 'SUPERADMIN', 'SUPERVISOR']

# ==========================
# GESTIÓN DE CATEGORÍAS
# ==========================
class CategoryListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = ServiceCategory
    template_name = 'services/admin/category_list.html'
    context_object_name = 'categorias'
    def get_queryset(self):
        return ServiceCategory.objects.all().order_by('nombre')

class CategoryCreateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = ServiceCategory
    form_class = CategoryForm
    template_name = 'services/admin/category_form.html'
    success_url = reverse_lazy('admin_category_list')
    success_message = "Categoría creada correctamente"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Categoría'
        return context

class CategoryUpdateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ServiceCategory
    form_class = CategoryForm
    template_name = 'services/admin/category_form.html'
    success_url = reverse_lazy('admin_category_list')
    success_message = "Categoría actualizada"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar: {self.object.nombre}'
        return context

# ==========================
# GESTIÓN DE SERVICIOS
# ==========================
class ServiceListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Service
    template_name = 'services/admin/service_list.html'
    context_object_name = 'servicios'
    def get_queryset(self):
        return Service.objects.all().order_by('nombre')

class ServiceCreateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'services/admin/service_form.html'
    success_url = reverse_lazy('admin_service_list')
    success_message = "Servicio creado correctamente"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Servicio Médico'
        return context

class ServiceUpdateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'services/admin/service_form.html'
    success_url = reverse_lazy('admin_service_list')
    success_message = "Servicio actualizado correctamente"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar: {self.object.nombre}'
        return context

# ==========================
# GESTIÓN DE MEDICAMENTOS
# ==========================
class MedicationListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Medication
    template_name = 'services/admin/medication_list.html'
    context_object_name = 'medicamentos'
    def get_queryset(self):
        return Medication.objects.all().prefetch_related('pasos_esquema').order_by('nombre')

class MedicationCreateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = Medication
    form_class = MedicationForm
    template_name = 'services/admin/medication_form.html'
    success_url = reverse_lazy('admin_medication_list')
    success_message = "Medicamento agregado al catálogo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Medicamento'
        if self.request.POST:
            context['dose_steps'] = MedicationDoseStepFormSet(self.request.POST)
        else:
            context['dose_steps'] = MedicationDoseStepFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        dose_steps = context['dose_steps']
        with transaction.atomic():
            self.object = form.save()
            if dose_steps.is_valid():
                dose_steps.instance = self.object
                dose_steps.save()
        return super().form_valid(form)

class MedicationUpdateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Medication
    form_class = MedicationForm
    template_name = 'services/admin/medication_form.html'
    success_url = reverse_lazy('admin_medication_list')
    success_message = "Medicamento actualizado"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar: {self.object.nombre}'
        if self.request.POST:
            context['dose_steps'] = MedicationDoseStepFormSet(self.request.POST, instance=self.object)
        else:
            context['dose_steps'] = MedicationDoseStepFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        dose_steps = context['dose_steps']
        with transaction.atomic():
            self.object = form.save()
            if dose_steps.is_valid():
                dose_steps.instance = self.object
                dose_steps.save()
        return super().form_valid(form)

# --- ELIMINAR CATEGORÍA ---
class CategoryDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = ServiceCategory
    template_name = 'services/admin/confirm_delete.html'
    success_url = reverse_lazy('admin_category_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Eliminar Categoría'
        context['entidad'] = 'la categoría'
        context['cancel_url'] = self.success_url
        return context
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            context['error_message'] = f"No se puede eliminar la categoría '{self.object.nombre}' porque tiene servicios asociados."
            return render(request, self.template_name, context)

class ServiceDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Service
    template_name = 'services/admin/confirm_delete.html'
    success_url = reverse_lazy('admin_service_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Eliminar Servicio'
        context['entidad'] = 'el servicio'
        context['cancel_url'] = self.success_url
        return context

class MedicationDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Medication
    template_name = 'services/admin/confirm_delete.html'
    success_url = reverse_lazy('admin_medication_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Eliminar Medicamento'
        context['entidad'] = 'el medicamento'
        context['cancel_url'] = self.success_url
        return context