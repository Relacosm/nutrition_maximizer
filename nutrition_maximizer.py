from typing import List, Dict, Optional
from dataclasses import dataclass
import requests
import json
import re
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading

# ========================
# Config
# ========================
# Get your free API key from: https://api-ninjas.com/register
API_NINJAS_KEY = ""  # Replace with your actual key

# API Ninjas endpoints
NUTRITION_API_URL = "https://api.api-ninjas.com/v1/nutrition"
RECIPE_API_URL = "https://api.api-ninjas.com/v1/recipe"
HEADERS = {"X-Api-Key": API_NINJAS_KEY}

# Rate limiting
LAST_REQUEST_TIME = 0
MIN_REQUEST_INTERVAL = 0.1  # 100ms between requests

# ========================
# Data Model
# ========================
@dataclass
class Ingredient:
    name: str
    quantity: float      # grams available
    calories: float      # per gram
    protein: float       # per gram
    carbs: float         # per gram
    fat: float           # per gram

    def nutritional_score(self, nutrient: str) -> float:
        nutrient_value = getattr(self, nutrient)
        return nutrient_value / self.calories if self.calories > 0 else 0.0

@dataclass
class Recipe:
    title: str
    ingredients: str
    instructions: str
    servings: str
    nutrition_score: float = 0.0

# ========================
# Enhanced Fallback Nutrition Database
# ========================
NUTRITION_DB = {
    # Proteins
    "chicken breast": {"calories": 1.65, "protein": 0.31, "carbs": 0.0, "fat": 0.036},
    "chicken thigh": {"calories": 2.09, "protein": 0.26, "carbs": 0.0, "fat": 0.109},
    "chicken": {"calories": 2.39, "protein": 0.31, "carbs": 0.0, "fat": 0.14},
    "beef": {"calories": 2.5, "protein": 0.26, "carbs": 0.0, "fat": 0.20},
    "ground beef": {"calories": 2.54, "protein": 0.26, "carbs": 0.0, "fat": 0.20},
    "salmon": {"calories": 2.08, "protein": 0.25, "carbs": 0.0, "fat": 0.12},
    "tuna": {"calories": 1.32, "protein": 0.30, "carbs": 0.0, "fat": 0.006},
    "egg": {"calories": 1.55, "protein": 0.13, "carbs": 0.011, "fat": 0.11},
    "tofu": {"calories": 0.83, "protein": 0.17, "carbs": 0.019, "fat": 0.048},
    
    # Carbohydrates
    "rice": {"calories": 1.3, "protein": 0.028, "carbs": 0.28, "fat": 0.003},
    "brown rice": {"calories": 1.12, "protein": 0.023, "carbs": 0.23, "fat": 0.009},
    "pasta": {"calories": 1.31, "protein": 0.05, "carbs": 0.25, "fat": 0.011},
    "bread": {"calories": 2.65, "protein": 0.09, "carbs": 0.49, "fat": 0.032},
    "quinoa": {"calories": 1.20, "protein": 0.044, "carbs": 0.22, "fat": 0.019},
    "oats": {"calories": 3.89, "protein": 0.169, "carbs": 0.661, "fat": 0.069},
    "potato": {"calories": 0.77, "protein": 0.02, "carbs": 0.17, "fat": 0.001},
    "sweet potato": {"calories": 0.86, "protein": 0.02, "carbs": 0.20, "fat": 0.001},
    
    # Vegetables
    "broccoli": {"calories": 0.34, "protein": 0.028, "carbs": 0.07, "fat": 0.004},
    "spinach": {"calories": 0.23, "protein": 0.029, "carbs": 0.036, "fat": 0.004},
    "kale": {"calories": 0.43, "protein": 0.029, "carbs": 0.10, "fat": 0.007},
    "carrots": {"calories": 0.41, "protein": 0.009, "carbs": 0.096, "fat": 0.002},
    "bell pepper": {"calories": 0.26, "protein": 0.008, "carbs": 0.061, "fat": 0.002},
    "tomato": {"calories": 0.18, "protein": 0.009, "carbs": 0.039, "fat": 0.002},
    "onion": {"calories": 0.40, "protein": 0.011, "carbs": 0.093, "fat": 0.001},
    "garlic": {"calories": 1.49, "protein": 0.064, "carbs": 0.331, "fat": 0.005},
    
    # Fruits
    "banana": {"calories": 0.89, "protein": 0.011, "carbs": 0.23, "fat": 0.003},
    "apple": {"calories": 0.52, "protein": 0.003, "carbs": 0.14, "fat": 0.002},
    "orange": {"calories": 0.43, "protein": 0.009, "carbs": 0.087, "fat": 0.001},
    "berries": {"calories": 0.43, "protein": 0.005, "carbs": 0.096, "fat": 0.003},
    
    # Dairy & Others
    "milk": {"calories": 0.42, "protein": 0.034, "carbs": 0.05, "fat": 0.01},
    "greek yogurt": {"calories": 0.97, "protein": 0.17, "carbs": 0.061, "fat": 0.052},
    "cheese": {"calories": 4.02, "protein": 0.25, "carbs": 0.024, "fat": 0.33},
    "olive oil": {"calories": 8.84, "protein": 0.0, "carbs": 0.0, "fat": 1.0},
    "avocado": {"calories": 1.67, "protein": 0.020, "carbs": 0.017, "fat": 0.147},
    "nuts": {"calories": 6.07, "protein": 0.206, "carbs": 0.207, "fat": 0.540}
}

# ========================
# Enhanced API Functions
# ========================
def rate_limit():
    """Simple rate limiting to avoid API abuse"""
    global LAST_REQUEST_TIME
    current_time = time.time()
    time_since_last = current_time - LAST_REQUEST_TIME
    if time_since_last < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - time_since_last)
    LAST_REQUEST_TIME = time.time()

def test_api_connection():
    """Test if API Ninjas is working"""
    if not API_NINJAS_KEY or API_NINJAS_KEY == "your_api_key_here":
        return False, "API key not set"
    
    try:
        rate_limit()
        response = requests.get(NUTRITION_API_URL, 
                              headers=HEADERS, 
                              params={"query": "apple"},
                              timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                return True, "API working"
            else:
                return True, "API working (empty response)"
        elif response.status_code == 401:
            return False, "Invalid API key - check your key"
        elif response.status_code == 429:
            return False, "Rate limit exceeded - try again later"
        elif response.status_code == 400:
            return False, f"Bad request - API key format issue"
        else:
            return False, f"API error {response.status_code}"
    except Exception as e:
        return False, f"Connection error: {e}"

def clean_food_name(food_name: str) -> str:
    """Clean and normalize food name for better API results"""
    cleaned = re.sub(r'\s+', ' ', food_name.lower().strip())
    cooking_terms = ['cooked', 'raw', 'fresh', 'frozen', 'canned', 'dried']
    for term in cooking_terms:
        cleaned = re.sub(rf'\b{term}\b', '', cleaned).strip()
    cleaned = re.sub(r'\b\d+\s*(g|kg|oz|lb|pounds?|grams?)\b', '', cleaned).strip()
    return cleaned

def fetch_nutrition_api(food_name: str) -> Dict[str, float]:
    """Get nutrition info from API Ninjas or fallback database"""
    cleaned_name = clean_food_name(food_name)
    
    if cleaned_name in NUTRITION_DB:
        return NUTRITION_DB[cleaned_name]
    
    for db_food in NUTRITION_DB:
        if db_food in cleaned_name or cleaned_name in db_food:
            return NUTRITION_DB[db_food]
    
    try:
        rate_limit()
        response = requests.get(NUTRITION_API_URL, 
                              headers=HEADERS, 
                              params={"query": cleaned_name},
                              timeout=15)
        
        if response.status_code != 200:
            raise ValueError(f"API error {response.status_code}: {response.text}")
        
        data = response.json()
        
        if not data or len(data) == 0:
            raise ValueError(f"No nutrition data found for '{cleaned_name}'")
        
        item = data[0]
        
        nutrition = {
            "calories": float(item.get("calories", 0)) / 100.0,
            "protein": float(item.get("protein_g", 0)) / 100.0,
            "carbs": float(item.get("carbohydrates_total_g", 0)) / 100.0,
            "fat": float(item.get("fat_total_g", 0)) / 100.0,
        }
        
        return nutrition
        
    except Exception as e:
        raise ValueError(f"API lookup failed for '{food_name}': {e}")

def search_recipes_by_ingredients(ingredient_list: List[str], target_nutrient: str) -> List[Recipe]:
    """Search for recipes using the ingredients and rank by nutritional value"""
    queries = []
    
    if len(ingredient_list) > 0:
        queries.append(ingredient_list[0])
    
    if len(ingredient_list) > 1:
        queries.append(f"{ingredient_list[0]} {ingredient_list[1]}")
    
    if len(ingredient_list) <= 3:
        queries.append(" ".join(ingredient_list))
    
    queries.append(f"healthy {ingredient_list[0]}")
    if target_nutrient == "protein":
        queries.append(f"high protein {ingredient_list[0]}")
    elif target_nutrient == "carbs":
        queries.append(f"carb rich {ingredient_list[0]}")
    
    all_recipes = []
    
    for query in queries[:5]:
        try:
            rate_limit()
            response = requests.get(RECIPE_API_URL,
                                  headers=HEADERS,
                                  params={"query": query},
                                  timeout=15)
            
            if response.status_code == 200:
                recipes_data = response.json()
                for recipe_data in recipes_data:
                    recipe = Recipe(
                        title=recipe_data.get("title", "Unknown Recipe"),
                        ingredients=recipe_data.get("ingredients", ""),
                        instructions=recipe_data.get("instructions", ""),
                        servings=recipe_data.get("servings", "Unknown servings")
                    )
                    all_recipes.append(recipe)
                
        except Exception as e:
            continue
    
    unique_recipes = []
    seen_titles = set()
    
    for recipe in all_recipes:
        if recipe.title.lower() not in seen_titles:
            seen_titles.add(recipe.title.lower())
            
            score = 0
            recipe_text = (recipe.ingredients + " " + recipe.instructions).lower()
            
            for ingredient in ingredient_list:
                ingredient_clean = clean_food_name(ingredient)
                if ingredient_clean in recipe_text or ingredient.lower() in recipe_text:
                    score += 1
            
            for ingredient in ingredient_list:
                if ingredient.lower() in recipe_text:
                    score += 0.5
            
            recipe.nutrition_score = score
            unique_recipes.append(recipe)
    
    unique_recipes.sort(key=lambda r: r.nutrition_score, reverse=True)
    return unique_recipes[:5]

def optimize_recipe_portions(recipe: Recipe, ingredients: List[Ingredient], 
                           max_calories: float, target_nutrient: str) -> Dict:
    """Optimize ingredient portions within the recipe context"""
    sorted_ingredients = sorted(ingredients, 
                               key=lambda ing: ing.nutritional_score(target_nutrient), 
                               reverse=True)
    
    optimized_portions = {}
    total_calories = 0.0
    total_target_nutrient = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    
    for ing in sorted_ingredients:
        if total_calories >= max_calories:
            break
        if ing.calories <= 0:
            continue
        
        remaining_calories = max_calories - total_calories
        max_qty_by_calories = remaining_calories / ing.calories
        qty_to_use = min(ing.quantity, max_qty_by_calories)
        
        if qty_to_use <= 0:
            continue
        
        optimized_portions[ing.name] = qty_to_use
        calories_added = qty_to_use * ing.calories
        total_calories += calories_added
        total_target_nutrient += qty_to_use * getattr(ing, target_nutrient)
        total_protein += qty_to_use * ing.protein
        total_carbs += qty_to_use * ing.carbs
        total_fat += qty_to_use * ing.fat
    
    return {
        "portions": optimized_portions,
        "total_calories": total_calories,
        f"total_{target_nutrient}": total_target_nutrient,
        "total_protein": total_protein,
        "total_carbs": total_carbs,
        "total_fat": total_fat,
        "macros_breakdown": {
            "protein_percent": (total_protein * 4 / total_calories * 100) if total_calories > 0 else 0,
            "carbs_percent": (total_carbs * 4 / total_calories * 100) if total_calories > 0 else 0,
            "fat_percent": (total_fat * 9 / total_calories * 100) if total_calories > 0 else 0
        }
    }

# ========================
# GUI Application
# ========================
class RecipeGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🍽️ Smart Nutritional Recipe Generator v2.0")
        self.root.geometry("1000x800")  # Increased window size
        self.root.configure(bg='#f0f0f0')
        
        # Data storage
        self.ingredients = []
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_ingredient_tab()
        self.create_recipe_tab()
        
        # Test API connection on startup
        self.test_api_status()
    
    def create_ingredient_tab(self):
        """Create the ingredient input tab"""
        self.ingredient_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ingredient_frame, text="🥗 Add Ingredients")
        
        # Title
        title_label = tk.Label(self.ingredient_frame, text="Smart Nutritional Recipe Generator",
                              font=('Arial', 16, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        title_label.pack(pady=10)
        
        # API Status
        self.api_status_label = tk.Label(self.ingredient_frame, text="Checking API status...",
                                        font=('Arial', 10), bg='#f0f0f0', fg='#7f8c8d')
        self.api_status_label.pack(pady=(0, 10))
        
        # Input frame
        input_frame = ttk.LabelFrame(self.ingredient_frame, text="Add New Ingredient", padding=10)
        input_frame.pack(fill='x', padx=20, pady=10)
        
        # Ingredient name
        tk.Label(input_frame, text="Ingredient Name:").grid(row=0, column=0, sticky='w', pady=2)
        self.name_entry = ttk.Entry(input_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # Auto-fill button
        self.auto_fill_btn = ttk.Button(input_frame, text="🔍 Auto-Fill Nutrition",
                                       command=self.auto_fill_nutrition)
        self.auto_fill_btn.grid(row=0, column=2, padx=5, pady=2)
        
        # Quantity
        tk.Label(input_frame, text="Quantity (grams):").grid(row=1, column=0, sticky='w', pady=2)
        self.quantity_entry = ttk.Entry(input_frame, width=15)
        self.quantity_entry.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        # Nutrition values (per gram)
        tk.Label(input_frame, text="Nutrition per gram:").grid(row=2, column=0, columnspan=3, sticky='w', pady=(10, 2))
        
        # Calories
        tk.Label(input_frame, text="Calories:").grid(row=3, column=0, sticky='w', pady=2)
        self.calories_entry = ttk.Entry(input_frame, width=15)
        self.calories_entry.grid(row=3, column=1, sticky='w', padx=5, pady=2)
        
        # Protein
        tk.Label(input_frame, text="Protein (g):").grid(row=4, column=0, sticky='w', pady=2)
        self.protein_entry = ttk.Entry(input_frame, width=15)
        self.protein_entry.grid(row=4, column=1, sticky='w', padx=5, pady=2)
        
        # Carbs
        tk.Label(input_frame, text="Carbs (g):").grid(row=5, column=0, sticky='w', pady=2)
        self.carbs_entry = ttk.Entry(input_frame, width=15)
        self.carbs_entry.grid(row=5, column=1, sticky='w', padx=5, pady=2)
        
        # Fat
        tk.Label(input_frame, text="Fat (g):").grid(row=6, column=0, sticky='w', pady=2)
        self.fat_entry = ttk.Entry(input_frame, width=15)
        self.fat_entry.grid(row=6, column=1, sticky='w', padx=5, pady=2)
        
        # Add ingredient button - using Accent style for visibility
        add_btn = ttk.Button(input_frame, text="✅ Add Ingredient",
                           command=self.add_ingredient, style='Accent.TButton')
        add_btn.grid(row=7, column=0, columnspan=3, pady=10)
        
        # Make button more prominent
        add_btn.configure(width=20)
        
        # Ingredients list - increased height
        list_frame = ttk.LabelFrame(self.ingredient_frame, text="Your Ingredients", padding=10)
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        list_frame.configure(height=300)  # Set minimum height
        
        # Create frame for treeview and scrollbar - with more space
        tree_container = tk.Frame(list_frame)
        tree_container.pack(fill='both', expand=True, pady=(0, 15))  # More bottom padding
        
        # Treeview for ingredients - increased height
        columns = ('Name', 'Quantity (g)', 'Cal/g', 'Protein/g', 'Carbs/g', 'Fat/g')
        self.ingredients_tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=10)  # Increased from 8 to 10
        
        for col in columns:
            self.ingredients_tree.heading(col, text=col)
            self.ingredients_tree.column(col, width=120, anchor='center')
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(tree_container, orient='vertical', command=self.ingredients_tree.yview)
        self.ingredients_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.ingredients_tree.pack(side='left', fill='both', expand=True)
        tree_scroll.pack(side='right', fill='y')
        
        # Button frame for proper layout - with more padding
        button_frame = tk.Frame(list_frame)
        button_frame.pack(fill='x', pady=10)  # Increased padding
        
        # Remove ingredient button
        remove_btn = ttk.Button(button_frame, text="🗑️ Remove Selected",
                              command=self.remove_ingredient, width=20)  # Set fixed width
        remove_btn.pack(side='left', padx=(0, 10))  # More spacing between buttons
        
        # Clear all button
        clear_btn = ttk.Button(button_frame, text="🗑️ Clear All",
                             command=self.clear_ingredients, width=15)  # Set fixed width
        clear_btn.pack(side='left')
    
    def create_recipe_tab(self):
        """Create the recipe generation tab"""
        self.recipe_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.recipe_frame, text="🍳 Generate Recipes")
        
        # Configuration frame
        config_frame = ttk.LabelFrame(self.recipe_frame, text="Recipe Configuration", padding=10)
        config_frame.pack(fill='x', padx=20, pady=10)
        
        # Target calories
        tk.Label(config_frame, text="Maximum Calories:").grid(row=0, column=0, sticky='w', pady=5)
        self.max_calories_entry = ttk.Entry(config_frame, width=15)
        self.max_calories_entry.grid(row=0, column=1, padx=5, pady=5)
        self.max_calories_entry.insert(0, "500")  # Default value
        
        # Target nutrient
        tk.Label(config_frame, text="Maximize:").grid(row=1, column=0, sticky='w', pady=5)
        self.target_nutrient = ttk.Combobox(config_frame, values=['protein', 'carbs', 'fat'], 
                                          state='readonly', width=12)
        self.target_nutrient.grid(row=1, column=1, padx=5, pady=5)
        self.target_nutrient.set('protein')  # Default value
        
        # Generate button - using Accent style for visibility
        self.generate_btn = ttk.Button(config_frame, text="🚀 Generate Smart Recipes",
                                     command=self.generate_recipes_threaded,
                                     style='Accent.TButton')
        self.generate_btn.grid(row=2, column=0, columnspan=2, pady=15)
        
        # Make button more prominent
        self.generate_btn.configure(width=25)
        
        # Progress bar
        self.progress = ttk.Progressbar(config_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.recipe_frame, text="Generated Recipes", padding=10)
        results_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, height=20,
                                                    font=('Consolas', 9))
        self.results_text.pack(fill='both', expand=True)
        
        # Export button
        export_btn = ttk.Button(results_frame, text="💾 Export Results",
                              command=self.export_results)
        export_btn.pack(pady=5)
    
    def test_api_status(self):
        """Test API connection and update status"""
        def test_in_thread():
            working, status = test_api_connection()
            if working:
                self.api_status_label.config(text=f"✅ API Status: {status}", fg='#27ae60')
            else:
                self.api_status_label.config(text=f"⚠️ API Status: {status}", fg='#e74c3c')
        
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def auto_fill_nutrition(self):
        """Auto-fill nutrition data from API or database"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter an ingredient name first.")
            return
        
        def fetch_in_thread():
            try:
                self.auto_fill_btn.config(state='disabled', text='🔍 Fetching...')
                nutrition = fetch_nutrition_api(name)
                
                # Update GUI in main thread
                self.root.after(0, lambda: self.update_nutrition_fields(nutrition, True))
                
            except Exception as e:
                error_msg = f"Could not fetch nutrition data: {e}"
                self.root.after(0, lambda: messagebox.showwarning("Auto-fill Failed", error_msg))
            finally:
                self.root.after(0, lambda: self.auto_fill_btn.config(state='normal', text='🔍 Auto-Fill Nutrition'))
        
        threading.Thread(target=fetch_in_thread, daemon=True).start()
    
    def update_nutrition_fields(self, nutrition, success=True):
        """Update nutrition entry fields"""
        if success:
            self.calories_entry.delete(0, tk.END)
            self.calories_entry.insert(0, f"{nutrition['calories']:.4f}")
            
            self.protein_entry.delete(0, tk.END)
            self.protein_entry.insert(0, f"{nutrition['protein']:.4f}")
            
            self.carbs_entry.delete(0, tk.END)
            self.carbs_entry.insert(0, f"{nutrition['carbs']:.4f}")
            
            self.fat_entry.delete(0, tk.END)
            self.fat_entry.insert(0, f"{nutrition['fat']:.4f}")
    
    def add_ingredient(self):
        """Add ingredient to the list"""
        try:
            name = self.name_entry.get().strip()
            quantity = float(self.quantity_entry.get())
            calories = float(self.calories_entry.get())
            protein = float(self.protein_entry.get())
            carbs = float(self.carbs_entry.get())
            fat = float(self.fat_entry.get())
            
            if not name:
                messagebox.showwarning("Warning", "Please enter an ingredient name.")
                return
            
            if quantity <= 0:
                messagebox.showwarning("Warning", "Quantity must be positive.")
                return
            
            # Create ingredient
            ingredient = Ingredient(name, quantity, calories, protein, carbs, fat)
            self.ingredients.append(ingredient)
            
            # Add to treeview
            self.ingredients_tree.insert('', 'end', values=(
                name, f"{quantity:.0f}", f"{calories:.3f}", 
                f"{protein:.3f}", f"{carbs:.3f}", f"{fat:.3f}"
            ))
            
            # Clear entries
            self.name_entry.delete(0, tk.END)
            self.quantity_entry.delete(0, tk.END)
            self.calories_entry.delete(0, tk.END)
            self.protein_entry.delete(0, tk.END)
            self.carbs_entry.delete(0, tk.END)
            self.fat_entry.delete(0, tk.END)
            
            messagebox.showinfo("Success", f"Added {name} to your ingredients!")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for all fields.")
    
    def remove_ingredient(self):
        """Remove selected ingredient"""
        selected = self.ingredients_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an ingredient to remove.")
            return
        
        # Get index of selected item
        item = selected[0]
        index = self.ingredients_tree.index(item)
        
        # Remove from data and treeview
        del self.ingredients[index]
        self.ingredients_tree.delete(item)
        
        messagebox.showinfo("Success", "Ingredient removed!")
    
    def clear_ingredients(self):
        """Clear all ingredients"""
        if self.ingredients:
            if messagebox.askyesno("Confirm", "Clear all ingredients?"):
                self.ingredients.clear()
                for item in self.ingredients_tree.get_children():
                    self.ingredients_tree.delete(item)
                messagebox.showinfo("Success", "All ingredients cleared!")
    
    def generate_recipes_threaded(self):
        """Generate recipes in a separate thread"""
        if not self.ingredients:
            messagebox.showwarning("Warning", "Please add at least one ingredient.")
            return
        
        try:
            max_calories = float(self.max_calories_entry.get())
            if max_calories <= 0:
                raise ValueError("Calories must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for maximum calories.")
            return
        
        target_nutrient = self.target_nutrient.get()
        
        def generate_in_thread():
            try:
                # Start progress bar
                self.root.after(0, lambda: self.progress.start())
                self.root.after(0, lambda: self.generate_btn.config(state='disabled'))
                
                # Generate recipes
                output = self.generate_smart_recipe(self.ingredients, max_calories, target_nutrient)
                
                # Update results in main thread
                self.root.after(0, lambda: self.update_results(output))
                
            except Exception as e:
                error_msg = f"Recipe generation failed: {e}"
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            finally:
                # Stop progress bar and re-enable button
                self.root.after(0, lambda: self.progress.stop())
                self.root.after(0, lambda: self.generate_btn.config(state='normal'))
        
        threading.Thread(target=generate_in_thread, daemon=True).start()
    
    def generate_smart_recipe(self, ingredients: List[Ingredient], max_calories: float, 
                             target_nutrient: str) -> str:
        """Generate optimized recipes and return formatted output"""
        
        ingredient_names = [ing.name for ing in ingredients]
        
        output = []
        output.append("=" * 60)
        output.append("🧠 SMART NUTRITIONAL RECIPE GENERATOR")
        output.append("=" * 60)
        
        # Search for real recipes
        recipes = search_recipes_by_ingredients(ingredient_names, target_nutrient)
        
        if not recipes:
            output.append("❌ No recipes found. Generating custom optimization...")
            custom_output = self.display_custom_optimization(ingredients, max_calories, target_nutrient)
            output.extend(custom_output)
            return "\n".join(output)
        
        # Display found recipes with optimized portions
        output.append(f"\n🍽️ FOUND {len(recipes)} RECIPES FOR YOUR INGREDIENTS:")
        
        for i, recipe in enumerate(recipes, 1):
            output.append(f"\n{'=' * 50}")
            output.append(f"📖 RECIPE #{i}: {recipe.title}")
            output.append(f"👥 Servings: {recipe.servings}")
            output.append(f"⭐ Ingredient Match Score: {recipe.nutrition_score:.1f}/{len(ingredient_names)}")
            output.append('=' * 50)
            
            # Optimize portions for this recipe
            optimization = optimize_recipe_portions(recipe, ingredients, max_calories, target_nutrient)
            
            output.append(f"\n📋 OPTIMIZED INGREDIENTS (for max {target_nutrient.upper()}):")
            total_weight = 0
            for ing_name, quantity in optimization["portions"].items():
                output.append(f" • {ing_name.title()}: {quantity:.0f}g")
                total_weight += quantity
            
            output.append(f"\n📊 COMPLETE NUTRITIONAL BREAKDOWN:")
            output.append(f" 🔥 Total Calories: {optimization['total_calories']:.0f}")
            output.append(f" 💪 Protein: {optimization['total_protein']:.1f}g ({optimization['macros_breakdown']['protein_percent']:.1f}%)")
            output.append(f" 🍞 Carbs: {optimization['total_carbs']:.1f}g ({optimization['macros_breakdown']['carbs_percent']:.1f}%)")
            output.append(f" 🥑 Fat: {optimization['total_fat']:.1f}g ({optimization['macros_breakdown']['fat_percent']:.1f}%)")
            output.append(f" ⚖️ Total Weight: {total_weight:.0f}g")
            output.append(f" 🎯 Target {target_nutrient.title()}: {optimization[f'total_{target_nutrient}']:.1f}g")
            
            output.append(f"\n🛒 ORIGINAL RECIPE INGREDIENTS:")
            # Clean and display original ingredients
            orig_ingredients = recipe.ingredients.replace("|", "\n • ").strip()
            if orig_ingredients:
                output.append(f" • {orig_ingredients}")
            else:
                output.append(" • (No ingredient list provided)")
            
            output.append(f"\n👨‍🍳 COOKING INSTRUCTIONS:")
            # Clean and format instructions
            if recipe.instructions:
                instructions = recipe.instructions.replace(". ", ".\n").strip()
                # Split into steps and number them
                sentences = [s.strip() for s in instructions.split('\n') if s.strip()]
                for j, step in enumerate(sentences, 1):
                    output.append(f" {j}. {step}")
            else:
                output.append(" • (No instructions provided)")
            
            output.append(f"\n💡 OPTIMIZATION TIPS:")
            output.append(f" • Adjust ingredient ratios to match the optimized portions above")
            output.append(f" • This maximizes your {target_nutrient} intake within {max_calories} calories")
            if target_nutrient == "protein":
                output.append(" • Consider cooking methods that preserve protein (grilling, baking)")
            elif target_nutrient == "carbs":
                output.append(" • Pair with healthy fats for better satiety")
            elif target_nutrient == "fat":
                output.append(" • Use healthy fats like olive oil, avocado, or nuts")
            
            if i < len(recipes):
                output.append(f"\n{'_' * 50}")
        
        return "\n".join(output)
    
    def display_custom_optimization(self, ingredients: List[Ingredient], max_calories: float, 
                                   target_nutrient: str) -> List[str]:
        """Enhanced fallback: Display custom optimization when no recipes found"""
        sorted_ingredients = sorted(ingredients, 
                                   key=lambda ing: ing.nutritional_score(target_nutrient), 
                                   reverse=True)
        
        total_calories = 0.0
        recipe = {}
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        
        for ing in sorted_ingredients:
            if total_calories >= max_calories:
                break
            if ing.calories <= 0:
                continue
            
            max_qty_by_calories = (max_calories - total_calories) / ing.calories
            qty_to_use = min(ing.quantity, max_qty_by_calories)
            if qty_to_use <= 0:
                continue
            
            recipe[ing.name] = qty_to_use
            total_calories += qty_to_use * ing.calories
            total_protein += qty_to_use * ing.protein
            total_carbs += qty_to_use * ing.carbs
            total_fat += qty_to_use * ing.fat
        
        target_amount = total_protein if target_nutrient == "protein" else \
                       total_carbs if target_nutrient == "carbs" else total_fat
        
        output = []
        output.append(f"\n🥗 CUSTOM OPTIMIZED RECIPE:")
        output.append(f"📋 INGREDIENTS:")
        total_weight = 0
        for ing, qty in recipe.items():
            output.append(f" • {ing.title()}: {qty:.0f}g")
            total_weight += qty
        
        output.append(f"\n📊 COMPLETE NUTRITION:")
        output.append(f" 🔥 Calories: {total_calories:.0f}")
        output.append(f" 💪 Protein: {total_protein:.1f}g")
        output.append(f" 🍞 Carbs: {total_carbs:.1f}g")
        output.append(f" 🥑 Fat: {total_fat:.1f}g")
        output.append(f" ⚖️ Total Weight: {total_weight:.0f}g")
        output.append(f" 🎯 Target {target_nutrient.title()}: {target_amount:.1f}g")
        
        output.append(f"\n👨‍🍳 BASIC PREPARATION GUIDE:")
        output.append(" 1. Prepare all ingredients by washing and chopping as needed")
        
        # Add specific cooking suggestions based on ingredients
        has_protein = any(ing for ing in sorted_ingredients if ing.protein > 0.15)
        has_vegetables = any(ing for ing in sorted_ingredients if ing.name.lower() in 
                            ['broccoli', 'spinach', 'carrots', 'bell pepper', 'kale'])
        
        if has_protein:
            output.append(" 2. Cook proteins first using your preferred method (grill, bake, or sauté)")
        if has_vegetables:
            output.append(" 3. Steam or sauté vegetables until tender-crisp")
        
        output.append(" 4. Combine ingredients according to your preference")
        output.append(" 5. Season to taste with salt, pepper, herbs, and spices")
        output.append(" 6. Serve immediately while hot")
        
        return output
    
    def update_results(self, output):
        """Update the results text area"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(1.0, output)
        # Switch to recipe tab to show results
        self.notebook.select(1)
    
    def export_results(self):
        """Export results to a text file"""
        content = self.results_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("Warning", "No results to export.")
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Recipe Results"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Results exported to {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {e}")

# ========================
# Quick ingredient preset functionality
# ========================
class IngredientPresets:
    """Quick presets for common ingredients"""
    
    PRESETS = {
        "Chicken Breast (200g)": {"quantity": 200, "calories": 1.65, "protein": 0.31, "carbs": 0.0, "fat": 0.036},
        "Brown Rice (150g)": {"quantity": 150, "calories": 1.12, "protein": 0.023, "carbs": 0.23, "fat": 0.009},
        "Broccoli (100g)": {"quantity": 100, "calories": 0.34, "protein": 0.028, "carbs": 0.07, "fat": 0.004},
        "Sweet Potato (200g)": {"quantity": 200, "calories": 0.86, "protein": 0.02, "carbs": 0.20, "fat": 0.001},
        "Salmon Fillet (150g)": {"quantity": 150, "calories": 2.08, "protein": 0.25, "carbs": 0.0, "fat": 0.12},
        "Greek Yogurt (100g)": {"quantity": 100, "calories": 0.97, "protein": 0.17, "carbs": 0.061, "fat": 0.052},
        "Quinoa (100g)": {"quantity": 100, "calories": 1.20, "protein": 0.044, "carbs": 0.22, "fat": 0.019},
        "Spinach (50g)": {"quantity": 50, "calories": 0.23, "protein": 0.029, "carbs": 0.036, "fat": 0.004},
    }

def add_preset_functionality(gui):
    """Add preset buttons to the GUI"""
    preset_frame = ttk.LabelFrame(gui.ingredient_frame, text="Quick Add Common Ingredients", padding=5)
    preset_frame.pack(fill='x', padx=20, pady=5)
    
    # Create preset buttons in a grid
    row = 0
    col = 0
    for name, data in IngredientPresets.PRESETS.items():
        btn = ttk.Button(preset_frame, text=name, width=20,
                        command=lambda n=name, d=data: add_preset_ingredient(gui, n, d))
        btn.grid(row=row, column=col, padx=2, pady=2, sticky='ew')
        
        col += 1
        if col > 3:  # 4 buttons per row
            col = 0
            row += 1
    
    # Configure column weights for even distribution
    for i in range(4):
        preset_frame.columnconfigure(i, weight=1)

def add_preset_ingredient(gui, name, data):
    """Add a preset ingredient to the GUI"""
    # Extract ingredient name without quantity info
    ingredient_name = name.split(" (")[0]
    
    # Fill the entry fields
    gui.name_entry.delete(0, tk.END)
    gui.name_entry.insert(0, ingredient_name)
    
    gui.quantity_entry.delete(0, tk.END)
    gui.quantity_entry.insert(0, str(data["quantity"]))
    
    gui.calories_entry.delete(0, tk.END)
    gui.calories_entry.insert(0, str(data["calories"]))
    
    gui.protein_entry.delete(0, tk.END)
    gui.protein_entry.insert(0, str(data["protein"]))
    
    gui.carbs_entry.delete(0, tk.END)
    gui.carbs_entry.insert(0, str(data["carbs"]))
    
    gui.fat_entry.delete(0, tk.END)
    gui.fat_entry.insert(0, str(data["fat"]))

# ========================
# Enhanced GUI with Styling
# ========================
def setup_styling(root):
    """Setup custom styling for the GUI"""
    style = ttk.Style()
    
    # Use a theme that works better with the system
    try:
        style.theme_use('clam')  # Better cross-platform theme
    except:
        style.theme_use('default')
    
    # Configure custom styles with better visibility
    style.configure('Accent.TButton', 
                   foreground='white', 
                   background='#2980b9',
                   font=('TkDefaultFont', 9, 'bold'))
    style.map('Accent.TButton',
              background=[('active', '#1f618d'),
                         ('pressed', '#1b4f72')])
    
    # Improve default button appearance
    style.configure('TButton',
                   font=('TkDefaultFont', 9),
                   padding=6)
    
    # Configure treeview colors
    style.configure("Treeview", 
                   background="#ffffff", 
                   foreground="#2c3e50",
                   fieldbackground="#ffffff")
    style.configure("Treeview.Heading", 
                   background="#34495e", 
                   foreground="white",
                   font=('TkDefaultFont', 9, 'bold'))
    style.map("Treeview.Heading",
              background=[('active', '#2c3e50')])
    
    # Configure labelframe
    style.configure("TLabelframe", 
                   background="#f8f9fa",
                   foreground="#2c3e50")
    style.configure("TLabelframe.Label",
                   background="#f8f9fa", 
                   foreground="#2c3e50",
                   font=('TkDefaultFont', 9, 'bold'))

# ========================
# Main Application Launch
# ========================
def main():
    """Launch the GUI application"""
    root = tk.Tk()
    
    # Setup styling
    setup_styling(root)
    
    # Create main GUI
    app = RecipeGeneratorGUI(root)
    
    # Add preset functionality
    add_preset_functionality(app)
    
    # Set minimum window size
    root.minsize(800, 600)
    
    # Center the window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Start the application
    root.mainloop()

# ========================
# CLI Interface (preserved for compatibility)
# ========================
def interactive():
    """Original CLI interface - preserved for compatibility"""
    print("🍽️ SMART NUTRITIONAL RECIPE GENERATOR v2.0")
    print("🤖 Powered by API Ninjas Recipe & Nutrition APIs")
    print("✨ Enhanced with better ingredient matching and nutrition analysis")
    
    # Check API key setup
    if API_NINJAS_KEY == "your_api_key_here":
        print("\n❌ API KEY SETUP REQUIRED:")
        print("   1. Get your free API key from: https://api-ninjas.com/register")
        print("   2. Replace 'your_api_key_here' with your actual key in the script")
        print("   3. The fallback database will be used for common ingredients")
        print("\n📚 Available in database:", ", ".join(list(NUTRITION_DB.keys())[:10]), "...")
    
    # Test API connection
    working, status = test_api_connection()
    if not working:
        print(f"⚠️ API Status: {status}")
        print("📚 Will use enhanced fallback database where available")
    else:
        print(f"✅ API Status: {status}")
    
    ingredients: List[Ingredient] = []
    
    print(f"\n🥗 Let's build your optimized recipe!")
    
    n = int(input("\nHow many ingredients do you have? "))
    
    for i in range(n):
        print(f"\n--- Ingredient {i+1} ---")
        name = input("Name: ").strip()
        
        while True:
            try:
                quantity = float(input("Quantity available (grams): "))
                if quantity > 0:
                    break
                else:
                    print("Please enter a positive number.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Try to fetch nutrition data
        try:
            fetched = fetch_nutrition_api(name)
            calories = fetched["calories"]
            protein = fetched["protein"]
            carbs = fetched["carbs"]
            fat = fetched["fat"]
            print(f"✅ Found: {calories:.3f} cal/g, {protein:.3f}g protein/g")
            
            # Ask if user wants to override
            override = input("Use these values? (y/n, default=y): ").strip().lower()
            if override == 'n':
                raise ValueError("User chose to override")
                
        except Exception as e:
            print(f"⚠️ Auto-fetch failed: {e}")
            print("Please enter nutrition values manually (per gram):")
            
            while True:
                try:
                    calories = float(input("Calories per gram: "))
                    protein = float(input("Protein per gram (g): "))
                    carbs = float(input("Carbs per gram (g): "))
                    fat = float(input("Fat per gram (g): "))
                    break
                except ValueError:
                    print("Please enter valid numbers.")
        
        ingredients.append(Ingredient(name, quantity, calories, protein, carbs, fat))
        print(f"✅ Added: {name}")
    
    # Get calorie target
    while True:
        try:
            max_calories = float(input("\nMaximum total calories for your meal: "))
            if max_calories > 0:
                break
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Get target nutrient
    print("\nWhich nutrient would you like to maximize?")
    print("1. Protein (for muscle building, satiety)")
    print("2. Carbs (for energy, endurance)")
    print("3. Fat (for hormone production, satiety)")
    
    while True:
        choice = input("Enter choice (1-3) or nutrient name: ").strip().lower()
        if choice in ['1', 'protein']:
            target_nutrient = 'protein'
            break
        elif choice in ['2', 'carbs', 'carbohydrates']:
            target_nutrient = 'carbs'
            break
        elif choice in ['3', 'fat', 'fats']:
            target_nutrient = 'fat'
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or the nutrient name.")
    
    print(f"\n🎯 Optimizing for maximum {target_nutrient.upper()}")
    print("⏳ Searching for recipes and optimizing...")
    
    # Create a temporary GUI instance for recipe generation
    class TempGUI:
        def generate_smart_recipe(self, ingredients, max_calories, target_nutrient):
            return RecipeGeneratorGUI(None).generate_smart_recipe(ingredients, max_calories, target_nutrient)
        def display_custom_optimization(self, ingredients, max_calories, target_nutrient):
            return RecipeGeneratorGUI(None).display_custom_optimization(ingredients, max_calories, target_nutrient)
    
    temp_gui = TempGUI()
    output = temp_gui.generate_smart_recipe(ingredients, max_calories, target_nutrient)
    print(output)
    
    print(f"\n🎉 Recipe generation complete!")
    print("💡 Tip: Try different target nutrients to see how your meal plan changes!")

if __name__ == "__main__":
    import sys
    
    # Check if user wants GUI or CLI
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        interactive()
    else:
        print("🍽️ Starting Smart Nutritional Recipe Generator GUI...")
        print("💡 Use --cli flag to run the command-line interface instead")
        main()