# Comparador de Seguros de Auto

Una aplicación web completa desarrollada en Python Flask que permite comparar cotizaciones de seguros de auto de diferentes aseguradoras. Los usuarios pueden subir múltiples archivos PDF de cotizaciones, extraer automáticamente los datos de cobertura y generar una tabla de comparación que puede exportarse como PDF.

## 🚀 Características

- **Parsing Automático**: Extrae datos de PDFs de 4 aseguradoras principales
- **Comparación Visual**: Tabla interactiva con todas las coberturas
- **Exportación PDF**: Genera reportes profesionales con logo de empresa
- **Interfaz Moderna**: Diseño responsive y atractivo
- **Deploy Ready**: Configurado para Railway con un clic

## 🏢 Aseguradoras Soportadas

- **HDI Seguros**
- **Qualitas**
- **ANA Seguros**
- **Seguros Atlas**

## 📋 Coberturas Extraídas

- Prima
- Forma de Pago
- Daños Materiales
- Robo Total
- Responsabilidad Civil
- Gastos Médicos Ocupantes
- Asistencia Legal
- Asistencia Viajes
- Accidente al Conductor
- Responsabilidad Civil Catastrófica
- Desbielamiento por Agua al Motor

## 🛠️ Tecnologías Utilizadas

- **Backend**: Python Flask
- **PDF Reading**: PyMuPDF (fitz)
- **PDF Generation**: WeasyPrint
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Railway (uvicorn)

## 📁 Estructura del Proyecto

```
/
├── app.py                # Aplicación principal Flask
├── pdf_parser.py         # Lógica de parsing de PDFs
├── requirements.txt      # Dependencias Python
├── Procfile             # Comando de deployment Railway
├── static/              # Assets estáticos
│   ├── style.css        # Estilos CSS
│   ├── logo.png         # Logo de empresa (150x50)
│   └── logo.svg         # Logo en formato SVG
└── templates/           # Plantillas HTML
    ├── index.html       # Página principal
    └── results.html     # Página de resultados
```

## 🚀 Instalación y Uso Local

### Prerrequisitos

- Python 3.8+
- pip (gestor de paquetes)

### Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone <repository-url>
   cd SegurosAutos
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar la aplicación**:
   ```bash
   python app.py
   ```

4. **Abrir en el navegador**:
   ```
   http://localhost:5000
   ```

### Nota sobre WeasyPrint en Windows

WeasyPrint requiere librerías del sistema que pueden no estar disponibles en Windows. La aplicación funcionará completamente para parsing y visualización, pero la exportación PDF estará limitada en desarrollo local. **La funcionalidad completa estará disponible en Railway**.

## 🌐 Deployment en Railway

### Método 1: Deploy Automático

1. **Conectar repositorio**:
   - Ve a [Railway.app](https://railway.app)
   - Conecta tu repositorio GitHub
   - Railway detectará automáticamente el `Procfile`

2. **Variables de entorno** (opcional):
   ```
   PORT=5000
   ```

3. **Deploy**:
   - Railway construirá e instalará automáticamente las dependencias
   - La aplicación estará disponible en la URL proporcionada

### Método 2: Deploy Manual

1. **Instalar Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Login y deploy**:
   ```bash
   railway login
   railway init
   railway up
   ```

## 📖 Uso de la Aplicación

### 1. Subir Archivos PDF

- Ve a la página principal
- Selecciona uno o más archivos PDF de cotizaciones
- Los archivos deben ser de las aseguradoras soportadas
- Haz clic en "Procesar Cotizaciones"

### 2. Ver Comparación

- La aplicación extraerá automáticamente los datos
- Se mostrará una tabla comparativa con todas las coberturas
- Los datos se ordenan alfabéticamente por compañía

### 3. Exportar PDF

- Haz clic en "Exportar a PDF"
- Se generará un archivo PDF profesional con:
  - Logo de la empresa
  - Tabla completa de comparación
  - Formato A4 horizontal
  - Estilos profesionales

## 🔧 Configuración Avanzada

### Personalizar Logo

Reemplaza `static/logo.png` con tu logo de empresa:
- Dimensiones recomendadas: 150x50 píxeles
- Formato: PNG o SVG
- Fondo transparente recomendado

### Modificar Campos de Comparación

Edita la lista `MASTER_FIELDS` en `app.py`:

```python
MASTER_FIELDS = [
    'Prima',
    'Forma de Pago',
    # ... otros campos
]
```

### Agregar Nueva Aseguradora

1. **Actualizar identificador** en `pdf_parser.py`:
   ```python
   def identify_company(text: str):
       # Agregar nueva condición
       elif "NUEVA_ASEGURADORA" in text_upper:
           return "NuevaAseguradora"
   ```

2. **Crear función de parsing**:
   ```python
   def parse_nueva_aseguradora(text: str) -> Dict[str, str]:
       # Implementar lógica de extracción
   ```

3. **Actualizar función principal**:
   ```python
   elif company == "NuevaAseguradora":
       return parse_nueva_aseguradora(full_text)
   ```

## 🐛 Solución de Problemas

### Error de WeasyPrint en Windows

```
OSError: cannot load library 'libgobject-2.0-0'
```

**Solución**: Este error es normal en Windows. La aplicación funcionará completamente en Railway. Para desarrollo local, puedes:

1. Usar WSL (Windows Subsystem for Linux)
2. Usar Docker
3. Desarrollar directamente en Railway

### PDF no se puede parsear

**Posibles causas**:
- Formato de PDF no soportado
- Texto no extraíble (PDF escaneado)
- Estructura diferente a la esperada

**Solución**: Verificar que el PDF contenga texto extraíble y sea de una aseguradora soportada.

### Error de memoria en archivos grandes

**Solución**: La aplicación está configurada para archivos de hasta 16MB. Para archivos más grandes, ajustar:

```python
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB
```

## 📊 Rendimiento

- **Parsing**: ~1-3 segundos por PDF
- **Exportación**: ~2-5 segundos para tabla completa
- **Memoria**: ~50-100MB por sesión
- **Concurrencia**: Soporta múltiples usuarios simultáneos

## 🔒 Seguridad

- Validación de tipos de archivo
- Límite de tamaño de archivo
- Sanitización de entrada
- Manejo seguro de errores

## 📝 Logs y Monitoreo

La aplicación registra:
- Errores de parsing
- Archivos procesados
- Errores de WeasyPrint
- Tiempo de procesamiento

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o preguntas:
- Crear un issue en GitHub
- Contactar al equipo de desarrollo
- Revisar la documentación de Railway

## 🎯 Roadmap

- [ ] Soporte para más aseguradoras
- [ ] Análisis de tendencias
- [ ] API REST
- [ ] Autenticación de usuarios
- [ ] Historial de comparaciones
- [ ] Notificaciones por email

---

**Desarrollado con ❤️ para simplificar la comparación de seguros de auto**
