---
type: wiki
title: Sorting in JavaScript
summary: JavaScript includes a native sort function that varies in speed depending on the JavaScript engine.
category: overview
sources: raw/docs-note-js-array-sort.txt
---

# Sorting in JavaScript

JavaScript environments provide a sort method for arrays, with performance that depends on the engine and optimization techniques like Just-In-Time compilation.

## Background

JavaScript is a language often used in web browsers and servers. It includes a built-in sort method for arrays of data. Unlike Python, where sorting is uniform, JavaScript's sort can behave differently depending on which engine runs the code. Different browsers use different engines—Chrome uses V8, Firefox uses SpiderMonkey, Safari uses JavaScriptCore. Each engine has different optimizations. Modern JavaScript engines use a technique called Just-In-Time compilation. This means the engine watches your code run and speeds up the parts that run often. A sort function might run slowly the first time, but faster after the engine learns about it. This makes [[measuring-program-speed]] trickier in JavaScript because the first few runs look different from later runs. The sort method in JavaScript may use different algorithms depending on the size of the array being sorted. This is similar to Python's built-in sort. Understanding these differences matters for people who want to write fast JavaScript code, especially for games or interactive applications where speed affects how smoothly things feel.

## See also

Related:: [[jit-compilation]], [[measuring-program-speed]]
