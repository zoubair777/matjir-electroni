document.addEventListener('DOMContentLoaded', () => {
  const products = [
    { id: 1, name: 'Product A', price: 29.99 },
    { id: 2, name: 'Product B', price: 49.99 },
    { id: 3, name: 'Product C', price: 19.99 },
    // More products...
  ];

  const productList = document.getElementById('product-list');
  const productSearch = document.getElementById('product-search');

  const renderProducts = (filter = '') => {
    const filteredProducts = products.filter(product =>
      product.name.toLowerCase().includes(filter.toLowerCase())
    );

    productList.innerHTML = '';
    filteredProducts.forEach(product => {
      const productItem = document.createElement('div');
      productItem.className = 'p-4 bg-white rounded shadow';
      productItem.innerHTML = `
        <h2 class="font-bold text-lg">${product.name}</h2>
        <p class="text-sm">$${product.price.toFixed(2)}</p>
        <button class="mt-2 bg-green-500 text-white px-2 py-1 rounded" onclick="addToCart(${product.id})">Add to Cart</button>
      `;
      productList.appendChild(productItem);
    });
  };

  const cart = JSON.parse(localStorage.getItem('cart')) || [];

  window.addToCart = id => {
    const product = products.find(p => p.id === id);
    if (product) {
      cart.push(product);
      localStorage.setItem('cart', JSON.stringify(cart));
      alert(`${product.name} added to cart!`);
    }
  };

  productSearch.addEventListener('input', event => {
    renderProducts(event.target.value);
  });

  document.getElementById('view-cart').addEventListener('click', () => {
    alert(`Cart: \n${cart.map(item => item.name).join(', ')}`);
  });

  renderProducts();
});
