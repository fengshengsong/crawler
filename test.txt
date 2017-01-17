一直以来对JavaScript异步编程的理解都停留在理论层面上，直到最近在项目中遇到这样一个需求：页面有多个作业需要提交，作业中包括基本信息以及一些图片。首先需要发送这些信息给服务器然后服务器生成一个作业ID返回，页面获取ID并且和图片一起再提交给服务器。根据服务器的要求，每个作业都是一次ajax请求，然后每个作业里面每张图片也是一次ajax请求。所以说，这里想要实现的功能就是：多个外部ajax请求按顺序执行，也就是说这些外部ajax请求需要同步执行，每次执行完会有一些操作，并且在每个ajax请求内还有多个内部ajax请求，这些内部的ajax可以并发执行，并且只有在上一个外部ajax请求内的内部ajax请求都执行完成返回成功之后再去执行下一个外部ajax请求。然后在最后一个的外部ajax请求，也就是所有的ajax请求都完成之后还需要进行一些操作。那么如何实现这些功能呢？
首先想到的方法是可以将每个外部ajax请求设置为同步。例如：
```javascript
    //ajaxSetup可以设置每个ajax的默认设置
    $.ajaxSetup({
    	//设置为同步
        async: false,
    });
    var ajaxTasks = [ajaxTask1,ajaxTask2,ajaxTask3];
	$.ajax(ajaxTask1).then(function(data){
        $.ajax({
            method:'POST',
            url:url,
        }).then(function(data){
            console.log(data);
        });
    });
    $.ajax(ajaxTask2).then(function(data){
        $.ajax({
            method:'POST',
            url:url,
        }).then(function(data){
            console.log(data);
        });
    });
    $.ajax(ajaxTask3).then(function(data){
        $.ajax({
            method:'POST',
            url:url,
        }).then(function(data){
            console.log(data);
        });
    });
```
或者
```javascript
    for(var ajaxTask of ajaxTasks){
        $.ajax(ajaxTask).then(function(data){
            $.ajax({
                method:'POST',
                url:url,
            }).then(function(data){
                console.log(data);
            });
        });
    }
```
这样外部ajax请求的同步操作实现了，但是由于异步事件队列机制，在所有同步代码完成之前，then中的内部ajax请求并未发送，所以是不能满足所述需求的。同时将ajax设置为同步也会带来许多问题，所以这个方法不可用。
另一种曾经普遍使用的方法是将ajax请求嵌套起来实现外部ajax的同步执行，然后结合Promise.all实现内部ajax的并发操作。
```javascript
	$.ajax().then(function(data){
    	Promise.all().then(function(data){
        	$.ajax().then(function(data){
            	Promise.all().then(...);
            });
        });
    });
```
或者
```javascript
    $.ajax().then(function(data){
        return Promise.all();
    }).then(function(data){
        return $.ajax();
    }).then(function(data){
        return Promise.all();
    }).then(...);
```
这个方法是可以基本实现需求，但是对于不确定数目的ajax请求有点无能无力，并且ajax请求一多，满屏幕的嵌套回调和thenthenthen，就出现了所谓的回调地狱，调试起来也是很麻烦。
所以说上述方法对于实现文章开头所述的功能都是不太可行的。可以看到这些代码结构是有规律的，都是传入了类似的回调函数。那么我们可以把这个回调函数抽取出来，然后再根据需求传入到then中作为其回调函数。但是ajax请求是异步的，我们需要在每个ajax请求发出之后暂停程序的执行，等到ajax请求成功返回后给出一个信号，然后再执行下一步代码。
ES6带来了许多神器，Generator函数就是其中之一，依靠Generator函数我们可以暂停程序的执行，将执行权交出函数外，然后在函数外部进行一定操作后再将执行权交还给函数内部。关于Generator函数就不多说了，可以看这里。[]()
但是仅仅靠Generator函数是不能够很好的处理异步操作的。例如：
```javascript
    var tasks = [
        {"name":"feng"},
        {"name":"hello"},
        {"name":"world"},
    ];
    function* genPost(){
        for(var task of tasks){
            yield $.ajax({
                method:'POST',
                url:url,
                data:task,
            });
        }
    }
    var g = genPost();
    var res = g.next();
    while(!res.done){
        res.value.then(function(data){
            console.log(data);
        });
        res = g.next();
    }
```
这仅仅是将Generator函数内部代码依次执行完，并没有将异步操作转换为同步操作。此时需要手动地来管理异步操作的流程。
```javascript
	var g = genPost();
	var res1 = g.next();
    res1.value.then(function(data){
      	var res2 = g.next(data);
      	res2.value.then(function(data){
        	var res3 = g.next(data);
            res3.value.then(function(data){
            	//...
            });
      	});
    });
```
这基本上又回到了开始的回调地狱中。可以看到，我们需要在每个ajax请求完成后传入一个回调函数，在这个函数里执行Generator函数的下一步操作，如此不断重复，因此可以使用递归来自动完成这个函数的执行。
这就需要回调函数中能够交还函数的执行权，也就是进入Generator函数执行下一步代码。而Thunk函数恰好就是这样一个函数。这涉及到了一个概念，什么是Thunk函数？在JavaScript中，Thunk函数是这样一个函数，就是只接受一个回调函数作为其参数。这恰好与Generator函数不谋而合。当Generator函数yield语句后的返回值都是一个Thunk函数，那么这是传入那个回调函数就可以自动去执行下一步操作。那么两者相配合就可以将异步操作变为同步操作。例如：
```javascript
    var fs = require('fs');
    var thunkify = require('./thunkify.js');
    var readFile = thunkify(fs.readFile);
    function* thunkRead(){
        var f1 = yield readFile('1.txt');
        var f2 = yield readFile('2.txt');
        var f3 = yield readFile('3.txt');
        console.log(f1.toString());
        console.log(f2.toString());
        console.log(f3.toString());
    }
    function run(gen){
        var g = gen();
        function next(err,data){
            var res = g.next(data);
            if(res.done){
                return;
            }
            res.value(next);
        }
        next();
    }
    run(genPost);
    run(thunkRead);
```
因此Generator函数内部的每一个异步操作都必须是Thunk函数，或者说是可以执行其中回调函数的函数。我们不停地将回调函数next传入到每一步操作所得的结果`result.value`中去，则在`result.value`内部必须要有执行next的操作。

> Generator是一个异步操作的容器。它的自动执行需要一种机制，当异步操作有了结果，能够自动交回执行权。一种是回调函数，将异步操作包装成Thunk函数，在回调函数里面交回执行权。另一种是Promise 对象，将异步操作包装成Promise对象，用then方法交回执行权。

那么具体到我们的需求上来，借鉴Thunk函数和Generator函数，因为ajax请求返回的是Promise对象，我们可以将Promise与Generator函数结合起来，这就需要将run函数改造一下。
```javascript
    function run(gen){
        var g = gen();
        function next(data){
            var res = g.next(data);
            if(res.done){
                return;
            }
            var ajaxTasks = [...];
            Promise.all(ajaxTasks).then(function(data){
            	res.value.then(next);
            });
        }
        next();
    }
    run(genPost);
```
至此我们的需求大部分都解决了。那么如何判断所有ajax请求都结束了呢？我们可以在最外部将整个ajax请求包装成一个Promise对象，当Generator函数完成时调用resolve来告诉Promise对象任务全部完成了，然后就可以进行后续操作了。
```javascript
    function runner(gen){
        return new Promise(function(resolve,reject){
            var g = gen();
            function next(data){
                var res = g.next(data);
                if(res.done){
                    resolve(res.value);
                    return;
                }
                var ajaxTasks = [...];
                Promise.all(ajaxTasks).then(function(data){
                    res.value.then(next);
                });
            };
            next();
        });
    }
```
如果内部ajax请求也需要同步执行，可以将Promise.all替换成相应的Generator函数，也是相同的道理。但不能仅仅满足于此。异步编程是一件非常有趣的事情，有必要继续弄弄清楚。折腾这么多来看一下另一个神器co。
```javascript
    co(genPost).then(function(data){
        console.log('all done');
    });
```

短短几行代码就搞定了，这是因为co内部已经帮我们把事情都做好了，只不过是上面一系列过程更加完备的实现，但基本原理都是一样的，所以下一步就是去研究下co的源码，弄弄清楚大神们究竟是怎样写代码的。
