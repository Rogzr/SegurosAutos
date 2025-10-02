# 🚀 Railway Deployment Checklist

## ✅ Pre-Deployment Verification

### Core Files Present
- [x] `app.py` - Main Flask application
- [x] `pdf_parser.py` - PDF parsing logic
- [x] `requirements.txt` - Python dependencies
- [x] `Procfile` - Railway deployment command
- [x] `static/style.css` - CSS styling
- [x] `static/logo.png` - Company logo (150x50)
- [x] `templates/index.html` - Upload page
- [x] `templates/results.html` - Results page
- [x] `README.md` - Documentation

### Functionality Tests
- [x] Company identification working
- [x] PDF parsing functions working
- [x] Flask app creation successful
- [x] All routes registered correctly
- [x] Local server running on port 5000

## 🚀 Railway Deployment Steps

### Method 1: GitHub Integration (Recommended)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Insurance PDF Comparator"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy on Railway**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect the `Procfile` and deploy

3. **Verify Deployment**:
   - Check the deployment logs
   - Test the application URL
   - Upload a test PDF to verify functionality

### Method 2: Railway CLI

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Deploy**:
   ```bash
   railway login
   railway init
   railway up
   ```

## 🔧 Post-Deployment Configuration

### Environment Variables (Optional)
```
PORT=5000
```

### Custom Domain (Optional)
- Add custom domain in Railway dashboard
- Update DNS records as instructed

## 🧪 Testing After Deployment

### Basic Functionality
1. **Homepage Load**: Verify the upload page loads correctly
2. **File Upload**: Test uploading a PDF file
3. **PDF Parsing**: Verify data extraction works
4. **Results Display**: Check comparison table renders
5. **PDF Export**: Test PDF generation and download

### Sample Test Files
Create test PDFs with content like:
```
HDI SEGUROS
Total a Pagar: $15,000.00
Daños Materiales
Límite de Responsabilidad: $500,000
Deducible: 5%
```

## 📊 Monitoring

### Railway Dashboard
- Monitor CPU and memory usage
- Check deployment logs
- Set up alerts for errors

### Application Logs
- PDF parsing errors
- WeasyPrint issues
- File upload problems

## 🔄 Updates and Maintenance

### Code Updates
1. Make changes locally
2. Test with `python test_app.py`
3. Push to GitHub
4. Railway auto-deploys

### Dependency Updates
1. Update `requirements.txt`
2. Test locally
3. Deploy to Railway

## 🆘 Troubleshooting

### Common Issues

**Deployment Fails**:
- Check `Procfile` syntax
- Verify all dependencies in `requirements.txt`
- Check Railway logs

**PDF Parsing Errors**:
- Verify PDF contains extractable text
- Check company identification patterns
- Review parsing regex patterns

**WeasyPrint Issues**:
- Should work automatically on Railway
- Check Railway logs for specific errors
- Verify font availability

### Support Resources
- Railway Documentation: https://docs.railway.app
- Flask Documentation: https://flask.palletsprojects.com
- WeasyPrint Documentation: https://doc.courtbouillon.org/weasyprint

## ✅ Success Criteria

The deployment is successful when:
- [ ] Application loads without errors
- [ ] File upload works correctly
- [ ] PDF parsing extracts data accurately
- [ ] Comparison table displays properly
- [ ] PDF export generates correctly
- [ ] All 4 insurance companies are supported
- [ ] Application handles errors gracefully

---

**🎉 Congratulations! Your Insurance PDF Comparator is ready for production use!**
